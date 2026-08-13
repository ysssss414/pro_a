# IMA Integration — v0.1

## 定位

IMA 负责：

- 原始资料云存储；
- 知识库 RAG / 阅读；
- 正式 Current View 等生成成果承载。

pro_a 负责：

- Node / Claim / Relation；
- Current View 版本和 Proposal；
- Knowledge Gap / Research Question；
- Impact Propagation；
- IMA 对象映射。

## v0.1 需要手工在 IMA 创建

- `00_Research_Sources`
- `10_Research_Outputs`

然后把 ID 填入 `config.toml`。

## 文件上传链路

pro_a 的 `IMAClient.upload_file()` 实现：

1. `check_repeated_names`
2. `create_media`
3. 使用 IMA 返回的 COS 临时 `secret_id / secret_key / token / bucket_name / region / cos_key` 通过腾讯 COS Python SDK 上传
4. `add_knowledge`

原始 Source 上传到 `source_kb_id`；正式 Current View Markdown 上传到 `output_kb_id`。

## 为什么 Current View 不做“覆盖编辑”

Current View 是不可变认知快照，采用 `v_YYYYMMDD` 新文件版本，不需要依赖 IMA 的任意正文覆盖 API。旧版本保留。

## 凭证

仅从环境变量读取：

- `IMA_OPENAPI_CLIENTID`
- `IMA_OPENAPI_APIKEY`

不写进数据库，不写入日志，不提交 Git。
