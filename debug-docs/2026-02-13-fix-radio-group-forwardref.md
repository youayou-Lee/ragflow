# Bug 修复记录：Radio.Group 组件添加 forwardRef 支持

## 日期
2026-02-13

## 问题描述

在创建知识库页面点击时，浏览器控制台报错：

```
Warning: Function components cannot be given refs. Attempts to access this ref will fail. Did you mean to use React.forwardRef()?

Check the render method of `Slot.SlotClone`.
Group@http://localhost:9222/src/components/ui/radio.tsx:73:15
```

## 根本原因

`Radio.Group` 组件是一个普通的函数组件，无法接收 ref。当该组件被 Radix UI 的 `Slot.SlotClone` 组件包装使用时，Slot 会尝试传递 ref 给子组件，但普通函数组件无法接收 ref，导致警告。

## 修改内容

**文件**: `web/src/components/ui/radio.tsx`

**修改**:
1. 导入 `forwardRef` from React
2. 使用 `forwardRef` 包装 `Group` 组件
3. 将 ref 传递给内部的 div 元素

```diff
-import React, { useContext, useState } from 'react';
+import React, { forwardRef, useContext, useState } from 'react';

-function Group({ ... }: RadioGroupProps) {
+const Group = forwardRef<HTMLDivElement, RadioGroupProps>(
+  function Group({ ... }: RadioGroupProps, ref) {
     ...
     return (
       <RadioGroupContext.Provider ...>
-        <div className={...}>
+        <div ref={ref} className={...}>
           ...
         </div>
       </RadioGroupContext.Provider>
     );
-}
+  },
+);
```

## 验证结果

修改后，Vite 热更新自动生效，刷新浏览器后警告消失，创建知识库功能正常。

## 备注

- 使用命名函数 (`function Group`) 而不是箭头函数，以便在 React DevTools 中显示正确的组件名称
- ref 类型为 `HTMLDivElement`，与内部 div 元素类型一致
