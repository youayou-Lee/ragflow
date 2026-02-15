import { IModalManagerChildrenProps } from '@/components/modal-manager';
import { LlmIcon } from '@/components/svg-icon';
import { Modal } from '@/components/ui/modal/modal';
import { useGetFallbackConfig, useSetFallbackConfig } from '@/hooks/use-llm-request';
import { useFetchMyLlmList, useFetchLlmList } from '@/hooks/use-llm-request';
import { getRealModelName } from '@/utils/llm-util';
import { LlmModelType } from '@/constants/knowledge';
import { useEffect, useState, useCallback, useMemo } from 'react';
import { Select, Tag, Spin, Tabs } from 'antd';
import { useTranslate } from '@/hooks/common-hooks';

interface IProps extends Omit<IModalManagerChildrenProps, 'showModal'> {
  llmFactory: string;
  factoryTags?: string[]; // Supported model types for this factory
}

// Map UI tags to LlmModelType
const TAG_TO_MODEL_TYPE: Record<string, string> = {
  'LLM': LlmModelType.Chat,
  'TEXT EMBEDDING': LlmModelType.Embedding,
  'TEXT RE-RANK': LlmModelType.Rerank,
  'TTS': LlmModelType.Tts,
  'SPEECH2TEXT': LlmModelType.Speech2text,
  'IMAGE2TEXT': LlmModelType.Image2text,
};

const MODEL_TYPE_LABELS: Record<string, string> = {
  [LlmModelType.Chat]: 'Chat',
  [LlmModelType.Embedding]: 'Embedding',
  [LlmModelType.Rerank]: 'Rerank',
  [LlmModelType.Tts]: 'TTS',
  [LlmModelType.Speech2text]: 'Speech to Text',
  [LlmModelType.Image2text]: 'Image to Text',
};

const FallbackConfigModal = ({ visible, hideModal, llmFactory, factoryTags }: IProps) => {
  const { t } = useTranslate('setting');

  // State for each model type's fallback config
  const [configs, setConfigs] = useState<Record<string, { models: string[]; factories: string[] }>>({});
  const [activeTab, setActiveTab] = useState<string>('');

  const { setFallback, loading: saving } = useSetFallbackConfig();

  // Get all LLM list to find models for this factory
  const llmList = useFetchLlmList();

  // Get all configured factories (my_llm)
  const { data: myLlmList } = useFetchMyLlmList();

  // Determine supported model types from factory tags
  const supportedModelTypes = useMemo(() => {
    if (!factoryTags || factoryTags.length === 0) {
      return [LlmModelType.Chat]; // Default to chat
    }
    const types: string[] = [];
    for (const tag of factoryTags) {
      const normalizedTag = tag.trim().toUpperCase();
      const modelType = TAG_TO_MODEL_TYPE[normalizedTag];
      if (modelType && !types.includes(modelType)) {
        types.push(modelType);
      }
    }
    return types.length > 0 ? types : [LlmModelType.Chat];
  }, [factoryTags]);

  // Set initial active tab
  useEffect(() => {
    if (supportedModelTypes.length > 0 && !activeTab) {
      setActiveTab(supportedModelTypes[0]);
    }
  }, [supportedModelTypes, activeTab]);

  // Fetch fallback config for all model types
  const { data: allFallbackConfig, isLoading: configLoading } = useGetFallbackConfig(llmFactory);

  // Load configs when data arrives
  useEffect(() => {
    if (allFallbackConfig?.fallback_by_type) {
      const newConfigs: Record<string, { models: string[]; factories: string[] }> = {};
      for (const [modelType, config] of Object.entries(allFallbackConfig.fallback_by_type)) {
        newConfigs[modelType] = {
          models: config.models || [],
          factories: config.factories || [],
        };
      }
      setConfigs(newConfigs);
    }
  }, [allFallbackConfig]);

  // Get models for this factory filtered by model type
  const getFactoryModelsForType = useCallback((modelType: string) => {
    const models = llmList[llmFactory] || [];
    return models.filter((m: any) => {
      // Check if model supports this type
      const modelTypes = m.model_type || '';
      return modelTypes.includes(modelType) || modelTypes.toLowerCase().includes(modelType.toLowerCase());
    });
  }, [llmList, llmFactory]);

  // Get configured factories that support this model type
  const getConfiguredFactoriesForType = useCallback((modelType: string) => {
    const factories: string[] = [];
    for (const factoryName of Object.keys(myLlmList || {})) {
      if (factoryName === llmFactory) continue;
      // Check if this factory has any model of this type
      const factoryModels = llmList[factoryName] || [];
      const hasModelOfType = factoryModels.some((m: any) => {
        const modelTypes = m.model_type || '';
        return modelTypes.includes(modelType) || modelTypes.toLowerCase().includes(modelType.toLowerCase());
      });
      if (hasModelOfType) {
        factories.push(factoryName);
      }
    }
    return factories;
  }, [myLlmList, llmList, llmFactory]);

  // Handle save for current model type
  const handleSave = useCallback(async () => {
    if (!llmFactory) {
      console.error('llmFactory is empty');
      return;
    }
    // Save all configs for all supported model types
    for (const modelType of supportedModelTypes) {
      const config = configs[modelType] || { models: [], factories: [] };
      await setFallback({
        llm_factory: llmFactory,
        model_type: modelType,
        fallback_models: config.models,
        fallback_factories: config.factories,
      });
    }
    hideModal();
  }, [configs, supportedModelTypes, llmFactory, setFallback, hideModal]);

  // Reset state when modal closes
  useEffect(() => {
    if (!visible) {
      setConfigs({});
      setActiveTab('');
    }
  }, [visible]);

  // Update config for a model type
  const updateConfig = useCallback((modelType: string, field: 'models' | 'factories', value: string[]) => {
    setConfigs(prev => ({
      ...prev,
      [modelType]: {
        ...prev[modelType],
        models: prev[modelType]?.models || [],
        factories: prev[modelType]?.factories || [],
        [field]: value,
      },
    }));
  }, []);

  // Render config for a single model type
  const renderModelTypeConfig = (modelType: string) => {
    const currentConfig = configs[modelType] || { models: [], factories: [] };
    const factoryModels = getFactoryModelsForType(modelType);
    const configuredFactories = getConfiguredFactoriesForType(modelType);

    return (
      <div className="space-y-6 py-4">
        {/* Same-factory fallback models */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            {t('fallback.models')}
          </label>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            placeholder={t('fallback.modelsPlaceholder')}
            value={currentConfig.models}
            onChange={(value) => updateConfig(modelType, 'models', value)}
            options={factoryModels.map((m: any) => ({
              label: getRealModelName(m.llm_name),
              value: m.llm_name,
            }))}
            optionFilterProp="label"
            showSearch
            maxTagCount={5}
            maxTagPlaceholder={(omitted) => `+${omitted.length} more`}
            listHeight={200}
            getPopupContainer={(triggerNode) => triggerNode.parentNode as HTMLElement}
          />
          <p className="text-xs text-text-muted mt-1">
            {t('fallback.modelsDesc')}
          </p>
        </div>

        {/* Cross-factory fallback */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            {t('fallback.factories')}
          </label>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            placeholder={t('fallback.factoriesPlaceholder')}
            value={currentConfig.factories}
            onChange={(value) => updateConfig(modelType, 'factories', value)}
            options={configuredFactories.map((f) => ({
              label: f,
              value: f,
            }))}
            optionFilterProp="label"
            showSearch
            maxTagCount={5}
            maxTagPlaceholder={(omitted) => `+${omitted.length} more`}
            listHeight={200}
            getPopupContainer={(triggerNode) => triggerNode.parentNode as HTMLElement}
          />
          <p className="text-xs text-text-muted mt-1">
            {t('fallback.factoriesDesc')}
          </p>
        </div>

        {/* Current configuration preview */}
        {(currentConfig.models.length > 0 || currentConfig.factories.length > 0) && (
          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-text-secondary mb-2">
              {t('fallback.order')}
            </label>
            <div className="bg-bg-card rounded p-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <Tag color="blue">{llmFactory}</Tag>
                {currentConfig.models.map((m) => (
                  <Tag key={m} color="green">
                    {getRealModelName(m)}
                  </Tag>
                ))}
                {currentConfig.factories.map((f) => (
                  <Tag key={f} color="orange">
                    {f}
                  </Tag>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Generate tab items - eslint-disable-next-line react-hooks/exhaustive-deps
  const tabItems = supportedModelTypes.map((modelType) => ({
    key: modelType,
    label: MODEL_TYPE_LABELS[modelType] || modelType,
    children: renderModelTypeConfig(modelType),
  }));

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <LlmIcon name={llmFactory} width={24} />
          <span>{t('fallback.title')} - {llmFactory}</span>
        </div>
      }
      open={visible}
      onOpenChange={(open) => !open && hideModal()}
      onOk={handleSave}
      onCancel={hideModal}
      confirmLoading={saving}
      okText={t('save')}
      cancelText={t('cancel')}
      className="!w-[650px]"
    >
      {configLoading ? (
        <div className="flex justify-center py-8">
          <Spin />
        </div>
      ) : supportedModelTypes.length > 1 ? (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="small"
        />
      ) : (
        renderModelTypeConfig(supportedModelTypes[0] || LlmModelType.Chat)
      )}
    </Modal>
  );
};

export default FallbackConfigModal;
