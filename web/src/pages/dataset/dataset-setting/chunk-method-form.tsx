import { useFormContext, useWatch } from 'react-hook-form';

import { DocumentParserType } from '@/constants/knowledge';
import { useMemo } from 'react';
import { IndictmentConfiguration } from './configuration/indictment';
import { InterrogationConfiguration } from './configuration/interrogation';
import { NaiveConfiguration } from './configuration/naive';

const ConfigurationComponentMap = {
  [DocumentParserType.Naive]: NaiveConfiguration,
  [DocumentParserType.Interrogation]: InterrogationConfiguration,
  [DocumentParserType.Indictment]: IndictmentConfiguration,
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
