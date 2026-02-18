import { Button } from '@/components/ui/button';
import { TableCell, TableRow } from '@/components/ui/table';
import { IDocumentInfo } from '@/interfaces/database/document';
import { ISubDocument } from '@/interfaces/database/sub-document';
import { useMemo, useState } from 'react';
import SubdocCorrectionPanel from './subdoc-correction-panel';
import { useSubDocumentList } from './use-sub-document';

interface IProps {
  document: IDocumentInfo;
  colSpan: number;
}

export function SubDocumentListRow({ document, colSpan }: IProps) {
  const { data, isFetching } = useSubDocumentList(document.id, true);
  const [current, setCurrent] = useState<ISubDocument>();
  const [visible, setVisible] = useState(false);

  const list = useMemo(() => data.sub_documents || [], [data.sub_documents]);

  return (
    <>
      <TableRow>
        <TableCell colSpan={colSpan} className="bg-bg-card">
          <div className="px-4 py-2">
            <div className="text-sm font-medium mb-2">Sub-documents</div>
            {isFetching ? (
              <div className="text-sm text-text-secondary">Loading...</div>
            ) : list.length === 0 ? (
              <div className="text-sm text-text-secondary">
                No sub-documents
              </div>
            ) : (
              <div className="space-y-2">
                {list.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between rounded border border-border p-2"
                  >
                    <div className="text-sm flex gap-5">
                      <span>Type: {item.type}</span>
                      <span>
                        Page: {item.start_page}-{item.end_page}
                      </span>
                      <span>Status: {item.status}</span>
                      <span>
                        Confidence: {(item.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setCurrent(item);
                        setVisible(true);
                      }}
                    >
                      Correct
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TableCell>
      </TableRow>
      {visible && (
        <SubdocCorrectionPanel
          visible={visible}
          hideModal={() => setVisible(false)}
          docId={document.id}
          subDocument={current}
        />
      )}
    </>
  );
}
