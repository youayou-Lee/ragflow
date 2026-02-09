---
sidebar_position: 3
slug: /add_google_drive
sidebar_custom_props: {
  categoryIcon: SiGoogledrive
}
---
# 添加 Google Drive

## 1. 创建 Google Cloud 项目

您可以为 RAGFlow 创建一个专用项目，也可以使用现有的 Google Cloud 外部项目。

**步骤：**
1. 打开项目创建页面\
`https://console.cloud.google.com/projectcreate`
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image1.jpeg?raw=true)
2. 选择 **External** 作为受众
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image2.png?raw=true)
3. 点击 **Create**
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image3.jpeg?raw=true)

------------------------------------------------------------------------

## 2. 配置 OAuth 同意屏幕

1.  前往 **APIs & Services → OAuth consent screen**
2.  确保 **User Type = External**
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image4.jpeg?raw=true)
3.  通过输入电子邮件地址在 **Test Users** 下添加测试用户
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image5.jpeg?raw=true)
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image6.jpeg?raw=true)

------------------------------------------------------------------------

## 3. 创建 OAuth 客户端凭据

1.  导航至：\
    `https://console.cloud.google.com/auth/clients`
2.  创建一个 **Web Application**
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image7.png?raw=true)
3.  输入客户端名称
4.  添加以下 **Authorized Redirect URIs**：

```
http://localhost:9380/v1/connector/google-drive/oauth/web/callback
```

- 如果使用 Docker 部署：

**Authorized JavaScript origin:**
```
http://localhost:80
```

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image8.png?raw=true)

- 如果从源代码运行：

**Authorized JavaScript origin:**
```
http://localhost:9222
```

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image9.png?raw=true)

5.  保存后，点击 **Download JSON**。此文件稍后将上传到 RAGFlow。

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image10.png?raw=true)

------------------------------------------------------------------------

## 4. 添加作用域

1.  打开 **Data Access → Add or remove scopes**

2.  粘贴并添加以下条目：

```
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/drive.metadata.readonly
https://www.googleapis.com/auth/admin.directory.group.readonly
https://www.googleapis.com/auth/admin.directory.user.readonly
```

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image11.jpeg?raw=true)
3.  更新并保存更改

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image12.jpeg?raw=true)
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image13.jpeg?raw=true)

------------------------------------------------------------------------

## 5. 启用所需的 API
导航到 Google API 库：\
`https://console.cloud.google.com/apis/library`
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image14.png?raw=true)

启用以下 API：

- Google Drive API
- Admin SDK API
- Google Sheets API
- Google Docs API


![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image15.png?raw=true)

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image16.png?raw=true)

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image17.png?raw=true)

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image18.png?raw=true)

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image19.png?raw=true)

![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image21.png?raw=true)

------------------------------------------------------------------------

## 6. 在 RAGFlow 中添加 Google Drive 作为数据源

1.  进入 RAGFlow 内的 **Data Sources**
2.  选择 **Google Drive**
3.  上传之前下载的 JSON 凭据
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image22.jpeg?raw=true)
4.  输入共享的 Google Drive 文件夹链接（https://drive.google.com/drive），例如：
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image23.png?raw=true)

5.  点击 **Authorize with Google**
将出现一个浏览器窗口。
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image25.jpeg?raw=true)
点击：- **Continue** - **Select All → Continue** - 授权应该成功 - 选择 **OK** 添加数据源
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image26.jpeg?raw=true)
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image27.jpeg?raw=true)
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image28.png?raw=true)
![placeholder-image](https://github.com/infiniflow/ragflow-docs/blob/040e4acd4c1eac6dc73dc44e934a6518de78d097/images/google_drive/image29.png?raw=true)



