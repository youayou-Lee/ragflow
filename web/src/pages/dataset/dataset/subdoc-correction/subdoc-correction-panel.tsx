import PdfPreview from '@/components/document-preview/pdf-preview';
import { Button, ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ISubDocument } from '@/interfaces/database/sub-document';
import { api_host } from '@/utils/api';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { IHighlight } from 'react-pdf-highlighter';
import {
  useSubDocumentActions,
  useSubDocumentVersions,
} from './use-sub-document';

interface IPropsType {
  visible: boolean;
  hideModal: () => void;
  docId: string;
  subDocument?: ISubDocument;
}

const TYPE_OPTIONS = ['contract', 'invoice', 'report', 'appendix', 'other'];

export default function SubdocCorrectionPanel({
  visible,
  hideModal,
  docId,
  subDocument,
}: IPropsType) {
  const { t } = useTranslation();
  const [startPage, setStartPage] = useState<number>(
    subDocument?.start_page || 1,
  );
  const [endPage, setEndPage] = useState<number>(subDocument?.end_page || 1);
  const [type, setType] = useState<string>(subDocument?.type || 'other');
  const [mergeIds, setMergeIds] = useState<string>('');
  const [splitPage, setSplitPage] = useState<number>(
    subDocument?.end_page || 1,
  );
  const { data: versions } = useSubDocumentVersions(
    subDocument?.id || '',
    visible,
  );
  const { correctSubDoc, mergeSubDocs, splitSubDoc, rerunSubDocs, loading } =
    useSubDocumentActions();

  useEffect(() => {
    setStartPage(subDocument?.start_page || 1);
    setEndPage(subDocument?.end_page || 1);
    setType(subDocument?.type || 'other');
    setSplitPage(subDocument?.end_page || 1);
  }, [subDocument]);

  const fileUrl = `${api_host}/document/get/${docId}`;

  const highlights: IHighlight[] = useMemo(() => {
    const target = subDocument || { start_page: startPage, end_page: endPage };
    const pages = [] as number[];
    for (let i = target.start_page; i <= target.end_page; i += 1) {
      pages.push(i);
    }
    return pages.map((pageNumber) => ({
      id: `${pageNumber}`,
      comment: { text: '', emoji: '' },
      content: { text: '' },
      position: {
        pageNumber,
        boundingRect: { x1: 0, y1: 0, x2: 1, y2: 1, width: 1, height: 1 },
        rects: [{ x1: 0, y1: 0, x2: 1, y2: 1, width: 1, height: 1 }],
      },
    }));
  }, [subDocument, startPage, endPage]);

  const handleSave = async () => {
    if (!subDocument) return;
    await correctSubDoc({
      doc_id: docId,
      sub_document_id: subDocument.id,
      start_page: startPage,
      end_page: endPage,
      type,
    });
  };

  const handleMerge = async () => {
    const ids = mergeIds
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean);
    if (ids.length < 2) return;
    await mergeSubDocs({ doc_id: docId, sub_document_ids: ids, type });
  };

  const handleSplit = async () => {
    if (!subDocument) return;
    await splitSubDoc({
      doc_id: docId,
      sub_document_id: subDocument.id,
      split_page: splitPage,
    });
  };

  return (
    <Dialog open={visible} onOpenChange={hideModal}>
      <DialogContent className="max-w-[92vw] w-[1200px]">
        <DialogHeader>
          <DialogTitle>
            {t('knowledgeDetails.metadata.editMetadata')}
          </DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4 h-[70vh]">
          <div className="space-y-3 overflow-auto pr-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>Start Page</Label>
                <Input
                  type="number"
                  value={startPage}
                  onChange={(e) => setStartPage(Number(e.target.value) || 1)}
                />
              </div>
              <div>
                <Label>End Page</Label>
                <Input
                  type="number"
                  value={endPage}
                  onChange={(e) => setEndPage(Number(e.target.value) || 1)}
                />
              </div>
            </div>
            <div>
              <Label>Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="rounded border p-3 space-y-2">
              <div className="font-medium">Merge Sub-Documents</div>
              <Input
                placeholder="id1,id2,..."
                value={mergeIds}
                onChange={(e) => setMergeIds(e.target.value)}
              />
              <Button onClick={handleMerge} disabled={loading}>
                Merge
              </Button>
            </div>

            <div className="rounded border p-3 space-y-2">
              <div className="font-medium">Split Sub-Document</div>
              <Input
                type="number"
                value={splitPage}
                onChange={(e) => setSplitPage(Number(e.target.value) || 1)}
              />
              <Button onClick={handleSplit} disabled={loading}>
                Split
              </Button>
            </div>

            <div className="rounded border p-3">
              <div className="font-medium mb-2">Version History</div>
              <div className="text-sm text-text-secondary space-y-1 max-h-32 overflow-auto">
                {(versions.versions || []).map((item) => (
                  <div key={item.id}>
                    v{item.version} · {item.type} · p{item.start_page}-
                    {item.end_page}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <PdfPreview
            url={fileUrl}
            highlights={highlights}
            className="h-full"
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => rerunSubDocs(docId)}
            disabled={loading}
          >
            Re-run
          </Button>
          <ButtonLoading onClick={handleSave} loading={loading}>
            {t('common.save')}
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
