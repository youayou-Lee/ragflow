#!/usr/bin/env python3
#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""Main entry point for RAG evaluation framework.

This framework evaluates RAG system performance on retrieval accuracy
and answer correctness. It is designed with clear separation of concerns:

- Evaluation module: measures performance, does NOT change retrieval behavior
- Server-side configuration: handles embedding models, chunking, reranking, etc.

Usage:
    uv run python test/eval/run.py
    uv run python test/eval/run.py --case "曾庆成危险驾驶案"
    uv run python test/eval/run.py --config custom_config.yaml
"""

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

import yaml

# Add project root to path
sys_path = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(sys_path))

from test.eval.models import (
    BenchmarkReport,
    BenchmarkSummary,
    TestResult,
)
from test.eval.questions.parser import load_all_questions, load_questions_for_case
from test.eval.evaluator.matcher import AnswerMatcher
from test.eval.evaluator.setup import EvaluationSetup
from test.eval.evaluator.retrieval import RetrievalEvaluator
from test.eval.evaluator.chat import ChatEvaluator
from test.eval.report.json_report import save_json_report
from test.eval.report.md_report import save_md_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_evaluation(
    config: dict,
    case_filter: str = None,
    category_filter: str = None,
    cleanup: bool = True,
    base_path: str = "benchmark",
) -> BenchmarkReport:
    """
    Run the complete evaluation test.

    Args:
        config: Configuration dictionary
        case_filter: Optional case name filter
        category_filter: Optional category filter
        cleanup: Whether to cleanup resources after test
        base_path: Base path to benchmark directory

    Returns:
        BenchmarkReport with results
    """
    start_time = time.time()

    # Load questions
    logger.info("Loading questions...")
    if case_filter:
        questions = load_questions_for_case(case_filter, base_path)
    else:
        questions = load_all_questions(base_path)

    # Filter by category if specified
    if category_filter:
        questions = [q for q in questions if q.category.value == category_filter]

    logger.info(f"Loaded {len(questions)} questions")

    if not questions:
        raise RuntimeError("No questions found to test")

    # Initialize components
    setup = EvaluationSetup(
        base_url=config["server"]["base_url"],
        email=config["auth"]["email"],
        password=config["auth"]["password"],
    )

    # Get optional retrieval parameters (for development/debugging only)
    retrieval_config = config.get("retrieval", {})
    top_k = retrieval_config.get("top_k")  # None = use server default
    similarity_threshold = retrieval_config.get("similarity_threshold")  # None = use server default

    matcher = AnswerMatcher(
        coverage_threshold=config["matching"]["evidence"]["coverage_threshold"],
        negative_keywords=config["matching"]["gap"]["negative_keywords"],
    )

    # Login
    logger.info("Logging in...")
    setup.login()

    # Create dataset
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_name = f"{config['dataset']['name_prefix']}_{timestamp}"
    logger.info(f"Creating dataset: {dataset_name}")
    dataset_id = setup.create_dataset(
        name=dataset_name,
        embedding_model=config["dataset"]["embedding_model"],
        chunk_method=config["dataset"]["chunk_method"],
    )
    logger.info(f"Dataset created: {dataset_id}")

    # Upload and parse documents
    document_ids = []
    doc_case_map = {}
    case_doc_map = {}

    # Get unique case names from questions
    cases_needed = set(q.case for q in questions)

    for doc_config in config.get("test_cases", config.get("documents", [])):
        case_name = doc_config["name"]

        # Skip documents not needed for filtered questions
        if cases_needed and case_name not in cases_needed:
            logger.info(f"Skipping document for other case: {case_name}")
            continue

        doc_path = Path(base_path).parent / doc_config["path"]

        logger.info(f"Uploading document: {doc_path}")
        doc_id = setup.upload_document(dataset_id, str(doc_path))
        document_ids.append(doc_id)
        doc_case_map[doc_id] = case_name
        case_doc_map[case_name] = doc_id
        logger.info(f"Document uploaded: {doc_id}")

    logger.info("Triggering document parsing...")
    setup.parse_document(dataset_id, document_ids)

    logger.info("Waiting for parsing to complete...")
    setup.wait_for_parsing(
        dataset_id,
        document_ids,
        timeout=config["test"]["parse_timeout"],
        interval=config["test"]["parse_interval"],
    )
    logger.info("Parsing completed")

    # Create chat assistant
    chat_name = f"eval_chat_{timestamp}"
    logger.info(f"Creating chat assistant: {chat_name}")
    chat_id = setup.create_chat_assistant(
        name=chat_name,
        dataset_ids=[dataset_id],
        llm_model=config["chat"]["llm_model"],
    )
    logger.info(f"Chat assistant created: {chat_id}")

    # Initialize evaluators
    retrieval_eval = RetrievalEvaluator(setup.session, config["server"]["base_url"])
    chat_eval = ChatEvaluator(setup.session, config["server"]["base_url"])

    # Run tests
    results: list[TestResult] = []

    for i, q in enumerate(questions, 1):
        logger.info(f"Testing question {i}/{len(questions)}: {q.question[:50]}...")

        try:
            test_start = time.time()

            # Get document ID for this case
            doc_id_for_case = case_doc_map.get(q.case)
            doc_ids_filter = [doc_id_for_case] if doc_id_for_case else None

            # Retrieval (using server defaults unless override specified)
            chunks, retrieval_time = retrieval_eval.retrieve(
                question=q.question,
                dataset_ids=[dataset_id],
                document_ids=doc_ids_filter,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            # Chat
            answer, chat_data, chat_time = chat_eval.chat(
                chat_id=chat_id,
                question=q.question,
                doc_ids=doc_ids_filter,
            )

            total_time = (time.time() - test_start) * 1000

            # Match answer
            match_result = matcher.match(q.category, q.expected_answer, answer)

            # Create test result
            result = TestResult(
                question_id=q.id,
                question=q.question,
                expected_answer=q.expected_answer,
                actual_answer=answer,
                matched=match_result.matched,
                score=match_result.score,
                category=q.category,
                case=q.case,
                retrieved_chunks=chunks,
                retrieval_count=len(chunks),
                retrieval_time_ms=retrieval_time,
                chat_time_ms=chat_time,
                total_time_ms=total_time,
            )

            status = "✓" if result.matched else "✗"
            logger.info(f"  {status} Score: {result.score:.2f} | Time: {total_time:.0f}ms")

        except Exception as e:
            logger.error(f"  Error: {e}")
            result = TestResult(
                question_id=q.id,
                question=q.question,
                expected_answer=q.expected_answer,
                actual_answer="",
                matched=False,
                score=0.0,
                category=q.category,
                case=q.case,
                error=str(e),
            )

        results.append(result)

    # Generate summary
    summary = BenchmarkSummary()
    summary.calculate(results)

    # Create report
    report = BenchmarkReport(
        timestamp=datetime.now().isoformat(),
        config={
            "dataset_name": dataset_name,
            "chat_name": chat_name,
            "retrieval_params": {
                "top_k": top_k if top_k else "server_default",
                "similarity_threshold": similarity_threshold if similarity_threshold else "server_default",
            },
        },
        summary=summary,
        results=results,
    )

    # Cleanup
    if cleanup:
        logger.info("Cleaning up resources...")
        setup.delete_chat_assistant(chat_id)
        setup.delete_dataset(dataset_id)
        logger.info("Cleanup completed")

    total_time = time.time() - start_time
    logger.info(f"Evaluation completed in {total_time:.1f}s")
    logger.info(f"Results: {summary.passed}/{summary.total} passed ({summary.score:.1%})")

    return report


def main():
    parser = argparse.ArgumentParser(description="Run RAG evaluation benchmark tests")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Filter by case name",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["factual", "evidence", "gap"],
        default=None,
        help="Filter by question category",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't cleanup resources after test",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default="benchmark",
        help="Base path to benchmark directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "reports",
        help="Output directory for reports",
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Run evaluation
    report = run_evaluation(
        config=config,
        case_filter=args.case,
        category_filter=args.category,
        cleanup=not args.no_cleanup,
        base_path=args.base_path,
    )

    # Save reports
    json_path = save_json_report(report, args.output_dir)
    logger.info(f"JSON report saved: {json_path}")

    md_path = save_md_report(report, args.output_dir)
    logger.info(f"Markdown report saved: {md_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total:   {report.summary.total}")
    print(f"Passed:  {report.summary.passed}")
    print(f"Failed:  {report.summary.failed}")
    print(f"Score:   {report.summary.score:.1%}")
    print("=" * 60)


if __name__ == "__main__":
    main()
