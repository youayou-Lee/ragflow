# RAGFlow 集成测试

本目录包含法律文档 RAG 系统的功能集成测试，按功能维度清晰分离测试类别。

## 测试架构

```
integration/
├── README.md                       # 本文档
├── conftest.py                     # pytest 夹具配置
│
├── test_upload.py                  # 1. 文件上传测试
│   ├── test_upload_single_file     #    - 单文件上传
│   └── test_upload_multiple_files  #    - 多文件上传
│
├── test_parse_indictment.py        # 2. 起诉意见书解析测试
│   ├── test_parse_single_indictment    #    - 单份解析
│   └── test_parse_multiple_indictments #    - 多份解析
│
├── test_parse_interrogation.py     # 3. 讯问笔录解析测试
│   ├── test_parse_single_interrogation     #    - 单份解析
│   └── test_parse_multiple_interrogations  #    - 多份解析
│
├── test_format_validation.py       # 4. 解析格式验证测试
│   ├── test_indictment_format      #    - 起诉意见书格式（chunk_type, 坐标等）
│   └── test_interrogation_format   #    - 讯问笔录格式
│
├── test_e2e.py                     # 5. 端到端测试
│   └── test_e2e_full_workflow      #    - 上传→解析→格式校验完整流程
│
└── fixtures/                       # 测试样本
    ├── sample_indictment.pdf
    └── sample_interrogation.pdf
```

## 测试分类说明

| 测试类型 | 数据策略 | 测试后清理 |
|---------|---------|----------|
| 上传测试 (`test_upload.py`) | 临时创建数据集 | ✅ 删除 |
| 解析测试（单份） | 预置知识库（1份文档，已解析完成） | ❌ 不删除 |
| 解析测试（多份） | 预置知识库（2份文档，已解析完成） | ❌ 不删除 |
| 格式验证测试 | 预置知识库（复用解析测试数据） | ❌ 不删除 |
| 端到端测试 (`test_e2e.py`) | 临时创建数据集 | ✅ 删除 |

## 运行方法

```bash
# 运行所有集成测试
uv run pytest test/eval/integration/ -v

# 按类别运行
uv run pytest test/eval/integration/test_upload.py -v
uv run pytest test/eval/integration/test_parse_indictment.py -v
uv run pytest test/eval/integration/test_parse_interrogation.py -v
uv run pytest test/eval/integration/test_format_validation.py -v
uv run pytest test/eval/integration/test_e2e.py -v

# 运行并显示打印输出
uv run pytest test/eval/integration/ -v -s

# 运行特定测试用例
uv run pytest test/eval/integration/test_upload.py::TestUpload::test_upload_single_file -v
```

## 前置条件

1. **RAGFlow 服务器** 运行在 `http://127.0.0.1:9380`
2. **配置文件** `test/eval/config.yaml` 包含正确的认证信息
3. **测试样本文件** 存在于 `fixtures/` 目录或 `benchmark/` 目录
4. **预置知识库** 已创建并完成解析（用于解析和格式测试）

## 预置数据准备

解析测试和格式验证测试使用预置知识库，需要手动创建：

### 1. 起诉意见书测试库_单份
```bash
# 创建知识库
# 上传 1 份 sample_indictment.pdf
# 触发解析，等待完成
# 记录知识库 ID 到 config.yaml
```

### 2. 起诉意见书测试库_多份
```bash
# 创建知识库
# 上传 2 份起诉意见书 PDF
# 触发解析，等待完成
# 记录知识库 ID 到 config.yaml
```

### 3. 讯问笔录测试库_单份
```bash
# 创建知识库
# 上传 1 份 sample_interrogation.pdf
# 触发解析，等待完成
# 记录知识库 ID 到 config.yaml
```

### 4. 讯问笔录测试库_多份
```bash
# 创建知识库
# 上传 2 份讯问笔录 PDF
# 触发解析，等待完成
# 记录知识库 ID 到 config.yaml
```

### 配置预置知识库 ID

编辑 `test/eval/config.yaml`，填入创建好的知识库 ID：

```yaml
prebuilt_datasets:
  indictment_single: "your-dataset-id-here"
  indictment_multiple: "your-dataset-id-here"
  interrogation_single: "your-dataset-id-here"
  interrogation_multiple: "your-dataset-id-here"
```

## 格式验证说明

每个 chunk 必须包含的坐标信息：

```python
{
    "position_int": [[page, left, right, top, bottom], ...],  # 必须有
    "page_num_int": [1, 2, ...],                              # 必须有
    "chunk_type": "section|qa_pair|...",                      # 按文书类型验证
    "bbox_union": [x1, y1, x2, y2],                           # 可选
}
```

### 起诉意见书 chunk_type
- `section` - 章节
- `paragraph` - 段落
- `evidence_item` - 证据项

### 讯问笔录 chunk_type
- `header` - 头部信息
- `qa_pair` - 问答对
- `qa_sub` - 问答子分段

## 扩展指南：添加新文书类型测试

### 1. 准备测试样本

将样本 PDF 放入 `fixtures/` 目录：

```
test/eval/integration/fixtures/sample_newdoctype.pdf
```

### 2. 更新 conftest.py

在 `sample_files()` 夹具中添加新样本：

```python
samples = {
    "indictment": fixtures_dir / "sample_indictment.pdf",
    "interrogation": fixtures_dir / "sample_interrogation.pdf",
    "newdoctype": fixtures_dir / "sample_newdoctype.pdf",  # 新增
}
```

### 3. 创建解析测试文件

复制 `test_parse_indictment.py` 并修改：

```python
# test_parse_newdoctype.py

class TestParseNewDocType:
    """Test suite for new document type parsing."""

    def test_parse_single_newdoctype(
        self,
        integration_setup: EvaluationSetup,
        newdoctype_single_dataset: str,  # 需要添加对应夹具
    ):
        # ...
```

### 4. 添加预置数据集夹具

在 `conftest.py` 中添加：

```python
@pytest.fixture
def newdoctype_single_dataset(
    integration_setup: EvaluationSetup,
    prebuilt_dataset_ids: dict[str, Optional[str]],
) -> str:
    dataset_id = prebuilt_dataset_ids.get("newdoctype_single")
    if not dataset_id:
        pytest.skip("Prebuilt newdoctype_single dataset not configured.")
    return dataset_id
```

### 5. 更新格式验证

在 `test_format_validation.py` 中定义新的 chunk_type：

```python
NEWDOCTYPE_CHUNK_TYPES = {"type1", "type2", "type3"}
```

并添加对应的格式验证测试：

```python
def test_newdoctype_format(
    self,
    integration_setup: EvaluationSetup,
    newdoctype_single_dataset: str,
):
    # ...
```

### 6. 更新配置文件

在 `config.yaml` 中添加预置数据集配置：

```yaml
prebuilt_datasets:
  # ... 现有配置
  newdoctype_single: ""
  newdoctype_multiple: ""
```

### 7. 创建预置知识库

按照上述"预置数据准备"步骤创建新的知识库。

## 可用夹具

| 夹具名称 | 用途 | 作用域 |
|---------|------|--------|
| `integration_setup` | 已登录的 API 客户端 | module |
| `sample_files` | 测试样本文件路径字典 | module |
| `test_config` | 测试配置字典 | function |
| `prebuilt_dataset_ids` | 预置知识库 ID 字典 | module |
| `indictment_single_dataset` | 单份起诉意见书数据集 | function |
| `indictment_multiple_dataset` | 多份起诉意见书数据集 | function |
| `interrogation_single_dataset` | 单份讯问笔录数据集 | function |
| `interrogation_multiple_dataset` | 多份讯问笔录数据集 | function |
| `temp_dataset_for_upload` | 临时数据集（上传测试用） | function |
| `temp_dataset_for_e2e` | 临时数据集（端到端测试用） | function |

## 代码复用

| 来源 | 复用内容 |
|------|----------|
| `test/eval/evaluator/setup.py` | `EvaluationSetup` 类 |
| `test/eval/config.yaml` | 服务器配置、认证信息 |
