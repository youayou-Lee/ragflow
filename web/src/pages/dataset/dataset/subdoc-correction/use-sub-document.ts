import message from '@/components/ui/message';
import { DocumentApiAction } from '@/hooks/use-document-request';
import {
  ISubDocument,
  ISubDocumentVersion,
} from '@/interfaces/database/sub-document';
import {
  correctSubDocument,
  listSubDocumentVersions,
  listSubDocuments,
  mergeSubDocuments,
  rerunSubDocuments,
  splitSubDocument,
} from '@/services/knowledge-service';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { get } from 'lodash';
import { useTranslation } from 'react-i18next';

export const SubDocumentApiAction = {
  List: 'listSubDocuments',
  Versions: 'listSubDocumentVersions',
};

export const useSubDocumentList = (docId: string, enabled: boolean) => {
  return useQuery<{ sub_documents: ISubDocument[]; total: number }>({
    queryKey: [SubDocumentApiAction.List, docId],
    enabled: enabled && !!docId,
    initialData: { sub_documents: [], total: 0 },
    queryFn: async () => {
      const ret = await listSubDocuments(docId);
      return get(ret, 'data.data', { sub_documents: [], total: 0 });
    },
  });
};

export const useSubDocumentVersions = (
  subDocumentId: string,
  enabled: boolean,
) => {
  return useQuery<{ versions: ISubDocumentVersion[] }>({
    queryKey: [SubDocumentApiAction.Versions, subDocumentId],
    enabled: enabled && !!subDocumentId,
    initialData: { versions: [] },
    queryFn: async () => {
      const ret = await listSubDocumentVersions(subDocumentId);
      return get(ret, 'data.data', { versions: [] });
    },
  });
};

export const useSubDocumentActions = () => {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const invalidate = async (docId: string) => {
    await queryClient.invalidateQueries({
      queryKey: [SubDocumentApiAction.List, docId],
    });
    await queryClient.invalidateQueries({
      queryKey: [DocumentApiAction.FetchDocumentList],
    });
  };

  const correctMutation = useMutation({
    mutationFn: correctSubDocument,
    onSuccess: async (_ret, vars) => {
      message.success(t('message.modified'));
      await invalidate(vars.doc_id);
    },
  });

  const mergeMutation = useMutation({
    mutationFn: mergeSubDocuments,
    onSuccess: async (_ret, vars) => {
      message.success(t('message.modified'));
      await invalidate(vars.doc_id);
    },
  });

  const splitMutation = useMutation({
    mutationFn: splitSubDocument,
    onSuccess: async (_ret, vars) => {
      message.success(t('message.modified'));
      await invalidate(vars.doc_id);
    },
  });

  const rerunMutation = useMutation({
    mutationFn: rerunSubDocuments,
    onSuccess: async (_ret, docId) => {
      message.success(t('message.operated'));
      await invalidate(docId);
    },
  });

  return {
    correctSubDoc: correctMutation.mutateAsync,
    mergeSubDocs: mergeMutation.mutateAsync,
    splitSubDoc: splitMutation.mutateAsync,
    rerunSubDocs: rerunMutation.mutateAsync,
    loading:
      correctMutation.isPending ||
      mergeMutation.isPending ||
      splitMutation.isPending ||
      rerunMutation.isPending,
  };
};
