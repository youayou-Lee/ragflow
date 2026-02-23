# 清理解析方案设计文档

## 背景

当前项目中存在多个解析方案（通用分块方法 + 刑事案件专用解析），导致代码复杂度高、维护困难。需要清理所有现有解析方案，保留一个干净的基础架构，便于后续重新开发适合法律文书的解析方法。

## 目标

1. 删除所有现有解析方案（通用 + 专用）
2. 保留 Layer A+B 架构的代码框架
3. 前端删除方法选择界面，但保留后续扩展能力
4. 测试模块只保留 eval 目录的基础配置

## 设计方案

### 1. 后端变更

#### 保留并改造
- `rag/app/naive.py` - 将 `criminal/blocks.py` 的 Layer A 功能合并进来，作为法律文书的通用解析入口

#### 删除
| 文件/目录 | 说明 |
|-----------|------|
| `rag/app/picture.py` | 图片分块方法 |
| `rag/app/tag.py` | 标签分块方法 |
| `rag/app/interrogation.py` | 讯问笔录入口 |
| `rag/app/indictment.py` | 起诉意见书入口 |
| `rag/app/scene_investigation.py` | 现场勘验入口 |
| `rag/app/criminal/` | 整个目录（合并 blocks.py 后删除） |

### 2. 前端变更

#### 删除
| 文件 | 说明 |
|------|------|
| `web/src/pages/dataset/dataset-setting/configuration/interrogation.tsx` | 讯问笔录配置组件 |
| `web/src/pages/dataset/dataset-setting/configuration/indictment.tsx` | 起诉意见书配置组件 |

#### 修改
| 文件 | 变更内容 |
|------|----------|
| `web/src/constants/knowledge.ts` | DocumentParserType 只保留 Naive |
| `web/src/pages/dataset/dataset-setting/chunk-method-form.tsx` | 移除刑事案件相关配置映射 |
| `web/src/locales/zh.ts` | 清理解析方法描述 |
| `web/src/locales/en.ts` | 清理解析方法描述 |

### 3. 测试模块

#### 删除
| 目录 | 说明 |
|------|------|
| `test/unit/` | 整个单元测试目录 |

#### 清空并保留模板
`test/eval/` 目录删除所有现有测试文件，保留：
- `config.yaml` - 基础配置（登录凭证、API 地址等）
- `test_template.py` - 最小化的测试模板文件

### 4. 最终结构

```
rag/app/
├── __init__.py
├── naive.py          # 唯一入口（含 Layer A 功能）
├── chunkers/         # 空目录（保留）
├── metadata/         # 保留
└── parsers/          # 空目录（保留）

test/
├── eval/
│   ├── config.yaml       # 基础配置
│   └── test_template.py  # 测试模板
└── (unit/ 已删除)

web/src/pages/dataset/dataset-setting/
├── chunk-method-form.tsx     # 简化后
├── configuration/
│   └── naive.tsx             # 保留
└── ...
```

## 后续工作

1. 基于 naive.py 改造，实现适合法律文书的通用解析方法（新 Layer A）
2. 后续根据需要开发新的 Layer B 插件
3. 前端重新设计解析方案选择界面
