export interface ISubDocument {
  id: string;
  doc_id: string;
  kb_id?: string;
  name?: string;
  type: string;
  start_page: number;
  end_page: number;
  status: string;
  confidence: number;
  version?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ISubDocumentVersion {
  id: string;
  sub_document_id: string;
  version: number;
  type: string;
  start_page: number;
  end_page: number;
  status: string;
  confidence: number;
  created_at?: string;
  created_by?: string;
}

export interface ISubDocumentListResponse {
  sub_documents: ISubDocument[];
  total: number;
}
