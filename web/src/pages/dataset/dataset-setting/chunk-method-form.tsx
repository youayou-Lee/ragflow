import { DocumentParserType } from '@/constants/knowledge';
import { useMemo } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { NaiveConfiguration } from './configuration/naive';

const ConfigurationComponentMap = {
  [DocumentParserType.Naive]: NaiveConfiguration,
};

function EmptyComponent() {
  return <div></div>;
}

export function ChunkMethodForm() {
  const form = useFormContext();

  const finalParserId: DocumentParserType = useWatch({
    control: form.control,
    name: 'parser_id',
  });

  const ConfigurationComponent = useMemo(() => {
    return finalParserId
      ? ConfigurationComponentMap[finalParserId]
      : EmptyComponent;
  }, [finalParserId]);

  return (
    <section className="h-full flex flex-col">
      <div className="overflow-auto flex-1 min-h-0">
        <ConfigurationComponent></ConfigurationComponent>
      </div>
    </section>
  );
}
