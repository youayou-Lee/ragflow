import Image from '@/components/image';
import { useTheme } from '@/components/theme-provider';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { IChunk, IChunkMetadata } from '@/interfaces/database/knowledge';
import { CheckedState } from '@radix-ui/react-checkbox';
import classNames from 'classnames';
import DOMPurify from 'dompurify';
import { useEffect, useState } from 'react';
import { ChunkTextMode } from '../../constant';
import styles from './index.module.less';

interface IProps {
  item: IChunk;
  checked: boolean;
  switchChunk: (available?: number, chunkIds?: string[]) => void;
  editChunk: (chunkId: string) => void;
  handleCheckboxClick: (chunkId: string, checked: boolean) => void;
  selected: boolean;
  clickChunkCard: (chunkId: string) => void;
  textMode: ChunkTextMode;
}

// Component to display metadata for interrogation chunks
const MetadataDisplay = ({ metadata, chunkType }: { metadata?: IChunkMetadata; chunkType?: string }) => {
  if (!metadata || Object.keys(metadata).length === 0) return null;

  const renderHeaderMetadata = () => {
    const items: { label: string; value?: string | string[] }[] = [
      { label: '时间', value: metadata.interrogation_time },
      { label: '地点', value: metadata.location },
      { label: '被讯问人', value: metadata.suspect_name },
      { label: '性别', value: metadata.suspect_gender },
      { label: '案件类型', value: metadata.case_type },
    ];

    const validItems = items.filter(item => item.value);
    if (validItems.length === 0) return null;

    return (
      <div className="flex flex-wrap gap-2 mt-2">
        {validItems.map((item, idx) => (
          <Badge key={idx} variant="outline" className="text-xs">
            <span className="text-muted-foreground mr-1">{item.label}:</span>
            <span>{Array.isArray(item.value) ? item.value.join(', ') : item.value}</span>
          </Badge>
        ))}
      </div>
    );
  };

  const renderQAMetadata = () => {
    const tags = metadata.tags || [];
    const entities = metadata.entities || {};
    const topic = metadata.topic;
    const keyFacts = metadata.key_facts || [];

    const allEntities: string[] = [
      ...(entities.persons || []),
      ...(entities.orgs || []),
      ...(entities.locations || []),
    ].filter(Boolean);

    if (tags.length === 0 && allEntities.length === 0 && !topic) return null;

    return (
      <div className="flex flex-wrap gap-2 mt-2">
        {topic && (
          <Badge variant="secondary" className="text-xs">
            {topic}
          </Badge>
        )}
        {tags.map((tag, idx) => (
          <Badge key={`tag-${idx}`} variant="outline" className="text-xs">
            {tag}
          </Badge>
        ))}
        {allEntities.slice(0, 5).map((entity, idx) => (
          <Badge key={`entity-${idx}`} variant="destructive" className="text-xs">
            {entity}
          </Badge>
        ))}
        {allEntities.length > 5 && (
          <Badge variant="outline" className="text-xs">
            +{allEntities.length - 5} 更多
          </Badge>
        )}
        {keyFacts.length > 0 && (
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="default" className="text-xs cursor-help">
                {keyFacts.length} 个关键事实
              </Badge>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              <ul className="list-disc list-inside text-sm">
                {keyFacts.map((fact, idx) => (
                  <li key={idx}>{fact}</li>
                ))}
              </ul>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    );
  };

  return chunkType === 'header' ? renderHeaderMetadata() : renderQAMetadata();
};

const ChunkCard = ({
  item,
  checked,
  handleCheckboxClick,
  editChunk,
  switchChunk,
  selected,
  clickChunkCard,
  textMode,
}: IProps) => {
  const available = Number(item.available_int);
  const [enabled, setEnabled] = useState(false);
  const { theme } = useTheme();

  const onChange = (checked: boolean) => {
    setEnabled(checked);
    switchChunk(available === 0 ? 1 : 0, [item.chunk_id]);
  };

  const handleCheck = (e: CheckedState) => {
    handleCheckboxClick(item.chunk_id, e === 'indeterminate' ? false : e);
  };

  const handleContentDoubleClick = () => {
    editChunk(item.chunk_id);
  };

  const handleContentClick = () => {
    clickChunkCard(item.chunk_id);
  };

  useEffect(() => {
    setEnabled(available === 1);
  }, [available]);
  const [open, setOpen] = useState<boolean>(false);
  return (
    <Card
      className={classNames('rounded-lg w-full py-3 px-3', {
        'bg-bg-title': selected,
        'bg-bg-input': !selected,
      })}
    >
      <div className="flex items-start justify-between gap-2">
        <Checkbox onCheckedChange={handleCheck} checked={checked}></Checkbox>
        {item.image_id && (
          <Popover open={open}>
            <PopoverTrigger
              asChild
              onMouseEnter={() => setOpen(true)}
              onMouseLeave={() => setOpen(false)}
            >
              <div>
                <Image id={item.image_id} className={styles.image}></Image>
              </div>
            </PopoverTrigger>
            <PopoverContent
              className="p-0"
              align={'start'}
              side={'right'}
              sideOffset={-20}
            >
              <div>
                <Image
                  id={item.image_id}
                  className={styles.imagePreview}
                ></Image>
              </div>
            </PopoverContent>
          </Popover>
        )}
        <section
          onDoubleClick={handleContentDoubleClick}
          onClick={handleContentClick}
          className={styles.content}
        >
          <div
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(item.content_with_weight),
            }}
            className={classNames(styles.contentText, {
              [styles.contentEllipsis]: textMode === ChunkTextMode.Ellipse,
            })}
          ></div>
        </section>
        <div>
          <Switch
            checked={enabled}
            onCheckedChange={onChange}
            aria-readonly
            className="!m-0"
          />
        </div>
      </div>

      {/* Display metadata for interrogation chunks */}
      <MetadataDisplay metadata={item.metadata} chunkType={item.chunk_type} />
    </Card>
  );
};

export default ChunkCard;
