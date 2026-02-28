import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { IReferenceChunk } from '@/interfaces/database/chat';
import { Button } from '../ui/button';

interface IProps {
  list: IReferenceChunk[];
  clickDocumentButton?: (documentId: string, chunk: IReferenceChunk) => void;
}

const normalizeSubDocType = (chunk: IReferenceChunk) =>
  (chunk.sub_doc_type || chunk.doc_type || '').toLowerCase();

const prioritySubDocTypes = new Set(['interrogation', 'indictment']);

const sortChunks = (list: IReferenceChunk[]) =>
  [...list].sort((a, b) => {
    const aPriority = prioritySubDocTypes.has(normalizeSubDocType(a)) ? 0 : 1;
    const bPriority = prioritySubDocTypes.has(normalizeSubDocType(b)) ? 0 : 1;
    if (aPriority !== bPriority) {
      return aPriority - bPriority;
    }
    const aPage = Array.isArray(a.page_num_int)
      ? (a.page_num_int[0] ?? Number.MAX_SAFE_INTEGER)
      : Number.MAX_SAFE_INTEGER;
    const bPage = Array.isArray(b.page_num_int)
      ? (b.page_num_int[0] ?? Number.MAX_SAFE_INTEGER)
      : Number.MAX_SAFE_INTEGER;
    return aPage - bPage;
  });

export function ReferenceCitationList({ list, clickDocumentButton }: IProps) {
  const sortedList = sortChunks(list || []);

  return (
    <section className="flex flex-col gap-2">
      {sortedList.map((item) => {
        const pageNo = Array.isArray(item.page_num_int)
          ? item.page_num_int[0]
          : undefined;
        const hasSubDoc = Boolean(
          item.sub_doc_id && item.sub_doc_id !== item.document_id,
        );

        return (
          <Card key={item.chunk_id || item.id}>
            <CardHeader className="py-2 px-3">
              <CardTitle className="text-sm flex items-center gap-2 flex-wrap">
                <span>{item.doc_name || item.document_name || '-'}</span>
                {item.sub_doc_type && (
                  <Badge variant="secondary">{item.sub_doc_type}</Badge>
                )}
                {typeof pageNo === 'number' && (
                  <Badge variant="outline">P{pageNo}</Badge>
                )}
                {prioritySubDocTypes.has(normalizeSubDocType(item)) && (
                  <Badge>P0</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 pb-3 px-3 flex flex-col gap-2">
              <p className="text-xs text-text-sub-title-invert line-clamp-3">
                {item.content || '-'}
              </p>
              {clickDocumentButton && item.document_id && (
                <Button
                  size="sm"
                  variant="link"
                  className="h-auto px-0 w-fit"
                  onClick={() => clickDocumentButton(item.document_id, item)}
                >
                  {hasSubDoc
                    ? `跳转到子文书定位 (${item.sub_doc_id})`
                    : '跳转到文档定位'}
                </Button>
              )}
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}
