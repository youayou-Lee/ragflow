# Bug 修复记录：禁用 whyDidYouRender 调试工具

## 日期
2026-02-13

## 问题描述

在本地启动 RAGFlow 前端服务后，注册账号并登录时，浏览器控制台报错：

```
Warning: React has detected a change in the order of Hooks called by RouterProvider.
Previous render            Next render
------------------------------------------------------
1. useContext                 useContext
2. useState                   useRef

Uncaught TypeError: can't access property "current", renderNumberForTheHook is undefined
    trackHookChanges whyDidYouRender.js:31
    WhyDidYouRenderReWrittenHook whyDidYouRender.js:198
```

## 根本原因

`@welldone-software/why-did-you-render` 是一个 React 调试工具，用于追踪组件的不必要重渲染。
该工具通过重写 React hooks 来追踪变化，但与当前的 React 18+ 和 react-router 版本存在兼容性问题，
导致 hooks 顺序在渲染之间发生变化，从而引发运行时错误。

## 修改内容

**文件**: `web/src/app.tsx`

**修改**: 注释掉 whyDidYouRender 的动态导入和配置代码

```diff
-if (process.env.NODE_ENV === 'development') {
-  import('@welldone-software/why-did-you-render').then(
-    (whyDidYouRenderModule) => {
-      const whyDidYouRender = whyDidYouRenderModule.default;
-      whyDidYouRender(React, {
-        trackAllPureComponents: true,
-        trackExtraHooks: [],
-        logOnDifferentValues: true,
-        exclude: [/^RouterProvider$/],
-      });
-    },
-  );
-}
+// Disabled due to compatibility issues with React 18+ / react-router
+// if (process.env.NODE_ENV === 'development') {
+//   import('@welldone-software/why-did-you-render').then(
+//     (whyDidYouRenderModule) => {
+//       const whyDidYouRender = whyDidYouRenderModule.default;
+//       whyDidYouRender(React, {
+//         trackAllPureComponents: true,
+//         trackExtraHooks: [],
+//         logOnDifferentValues: true,
+//         exclude: [/^RouterProvider$/],
+//       });
+//     },
+//   );
+// }
```

## 验证结果

修改后，Vite 热更新自动生效，刷新浏览器后错误消失，登录功能正常。

## 备注

- 该调试工具在开发环境中是可选的，禁用不影响正常功能
- 如需重新启用，需要等待 `@welldone-software/why-did-you-render` 发布兼容 React 18+ 的新版本
