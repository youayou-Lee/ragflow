import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog';
import {
  DynamicForm,
  DynamicFormRef,
  FormFieldConfig,
  FormFieldType,
} from '@/components/dynamic-form';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { DialogProps } from '@radix-ui/react-dialog';
import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { ControllerRenderProps } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

export const ReparseDialog = memo(
  ({
    handleOperationIconClick,
    chunk_num,
    enable_metadata = false,
    hidden = false,
    visible = true,
    hideModal,
  }: DialogProps & {
    chunk_num: number;
    handleOperationIconClick: (options?: {
      delete: boolean;
      apply_kb: boolean;
      reparse_type?: string;
    }) => void;
    enable_metadata?: boolean;
    visible: boolean;
    hideModal: () => void;
    hidden?: boolean;
  }) => {
    const [defaultValues, setDefaultValues] = useState<any>(null);
    const [fields, setFields] = useState<FormFieldConfig[]>([]);
    const { t } = useTranslation();
    const handleOperationIconClickRef = useRef(handleOperationIconClick);
    const hiddenRef = useRef(hidden);

    useEffect(() => {
      handleOperationIconClickRef.current = handleOperationIconClick;
      hiddenRef.current = hidden;
    });

    useEffect(() => {
      if (hiddenRef.current) {
        handleOperationIconClickRef.current();
      }
    }, []);
    useEffect(() => {
      setDefaultValues({
        delete: chunk_num > 0,
        apply_kb: false,
        reparse_type: 'full',
      });
      const deleteField = {
        name: 'delete',
        label: '',
        type: FormFieldType.Checkbox,
        render: (fieldProps: ControllerRenderProps) => (
          <div className="flex items-center text-text-secondary p-5 border border-border-button rounded-lg">
            <Checkbox
              {...fieldProps}
              checked={fieldProps.value}
              onCheckedChange={(checked: boolean) => {
                fieldProps.onChange(checked);
              }}
            />
            <span className="ml-2">
              {chunk_num > 0
                ? t(`knowledgeDetails.redo`, {
                    chunkNum: chunk_num,
                  })
                : t('knowledgeDetails.redoAll')}
            </span>
          </div>
        ),
      };
      const reparseTypeField = {
        name: 'reparse_type',
        label: t('knowledgeDetails.reparseType'),
        type: FormFieldType.Custom,
        defaultValue: 'full',
        render: (fieldProps: ControllerRenderProps) => (
          <div className="text-text-secondary p-5 border border-border-button rounded-lg space-y-3">
            <div className="font-medium mb-3">
              {t('knowledgeDetails.reparseType')}
            </div>
            <RadioGroup
              onValueChange={fieldProps.onChange}
              value={fieldProps.value || 'full'}
              className="space-y-3"
            >
              <div className="flex items-center space-x-3">
                <RadioGroupItem value="full" id="full" />
                <label htmlFor="full" className="cursor-pointer">
                  <span className="font-medium">
                    {t('knowledgeDetails.fullReparse')}
                  </span>
                  <span className="block text-sm text-text-secondary mt-1">
                    {t('knowledgeDetails.fullReparseDesc')}
                  </span>
                </label>
              </div>
              <div className="flex items-center space-x-3">
                <RadioGroupItem value="text_only" id="text_only" />
                <label htmlFor="text_only" className="cursor-pointer">
                  <span className="font-medium">
                    {t('knowledgeDetails.textOnlyReparse')}
                  </span>
                  <span className="block text-sm text-text-secondary mt-1">
                    {t('knowledgeDetails.textOnlyReparseDesc')}
                  </span>
                </label>
              </div>
            </RadioGroup>
          </div>
        ),
      };
      const applyKBField = {
        name: 'apply_kb',
        label: '',
        type: FormFieldType.Checkbox,
        defaultValue: false,
        render: (fieldProps: ControllerRenderProps) => (
          <div className="flex items-center text-text-secondary p-5 border border-border-button rounded-lg">
            <Checkbox
              {...fieldProps}
              checked={fieldProps.value}
              onCheckedChange={(checked: boolean) => {
                fieldProps.onChange(checked);
              }}
            />
            <span className="ml-2">
              {t('knowledgeDetails.applyAutoMetadataSettings')}
            </span>
          </div>
        ),
      };
      if (chunk_num > 0 && enable_metadata) {
        setFields([deleteField, reparseTypeField, applyKBField]);
      } else if (chunk_num > 0 && !enable_metadata) {
        setFields([deleteField, reparseTypeField]);
      } else if (chunk_num <= 0 && enable_metadata) {
        setFields([reparseTypeField, applyKBField]);
      } else {
        setFields([reparseTypeField]);
      }
    }, [chunk_num, t, enable_metadata]);

    const formCallbackRef = useRef<DynamicFormRef>(null);

    const handleCancel = useCallback(() => {
      // handleOperationIconClick(false);
      hideModal?.();
      // formInstance?.reset();
      formCallbackRef?.current?.reset();
    }, [formCallbackRef, hideModal]);

    const handleSave = useCallback(async () => {
      // const instance = formInstance;
      const instance = formCallbackRef?.current;
      if (!instance) {
        console.error('Form instance is null');
        return;
      }

      const check = await instance.trigger();
      if (check) {
        instance.submit();
        const formValues = instance.getValues();
        console.log(formValues);
        handleOperationIconClick({
          delete: formValues.delete,
          apply_kb: formValues.apply_kb,
          reparse_type: formValues.reparse_type || 'full',
        });
      }
    }, [formCallbackRef, handleOperationIconClick]);

    return (
      <ConfirmDeleteDialog
        title={t(`knowledgeDetails.parseFile`)}
        onOk={() => handleSave()}
        onCancel={() => handleCancel()}
        hidden={hidden}
        open={visible}
        okButtonText={t('common.confirm')}
        content={{
          title: t(`knowledgeDetails.parseFileTip`),
          node: (
            <div>
              <DynamicForm.Root
                onSubmit={(data) => {
                  console.log('submit', data);
                }}
                ref={formCallbackRef}
                fields={fields}
                defaultValues={defaultValues}
              >
                {/* <DynamicForm.CancelButton
                handleCancel={() => handleOperationIconClick(false)}
                cancelText={t('common.cancel')}
              />
              <DynamicForm.SavingButton
                buttonText={t('common.confirm')}
                submitFunc={handleSave}
              /> */}
              </DynamicForm.Root>
            </div>
          ),
        }}
      >
        {/* {children} */}
      </ConfirmDeleteDialog>
    );
  },
);

ReparseDialog.displayName = 'ReparseDialog';
