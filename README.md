# LCNA risk-control data packages

北美风控数据层包，供桌面项目 D1 导入生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）。全程只读取数；不含客户个人信息（手机号、邮箱、uid、IP 等均未取值）。

## 一个文件下载全部结果

- **[`LCNA_riskcontrol_results_all_20261010-1621.zip`](https://github.com/xiangyuzeng/lcna-riskcontrol-data-package/raw/main/LCNA_riskcontrol_results_all_20261010-1621.zip)**（约 14.8 MB）：五个包原样解压，合在一个 zip 里，顶层有 `README.md` 索引；sha256 见 `LCNA_riskcontrol_results_all_20261010-1621.zip.sha256`。五个包是：
  - `RC_patrol_20261010-1621/`：每日短信巡检 + 自动发飞书群，最新（取代 `RC_patrol_20261010-0736/`）；
  - `RC_data_20261010-0013/`；
  - `RC_data_20260927-0614/`；
  - `RC_data_20260926-1722/`；
  - `RC_data_20260925-0817/`。
- 合集隐私扫描 8,307 个文件，unresolved 0（放行 2 条：两轮的 Redis 平均 TTL，非个人信息）。
- 它取代同日 07:36 的五包合集（`LCNA_riskcontrol_results_all_20261010-0736.zip`，仍在提交 `8aedb29` 的历史里）；更早的合集在提交 `a4f49e0`、`93aebbb` 里。

## 最新：RC_patrol_20261010-1621（2026-10-10，每日 21:00 巡检 + 自动发飞书群）

- 包内容（已解压）：[`RC_patrol_20261010-1621/`](RC_patrol_20261010-1621/)
  - 入口：[`README.md`](RC_patrol_20261010-1621/README.md)（先看第 0 节「当前状态」）
  - **自动发群部署指南**（中文；在常开、有 cron 的机器上从零装好 cron + 飞书 webhook）：[`GUIDE_自动发群部署.md`](RC_patrol_20261010-1621/GUIDE_自动发群部署.md)
  - 运行卡 C（自动发群）：[`RUN_CARD_自动发群.md`](RC_patrol_20261010-1621/RUN_CARD_自动发群.md)
  - 运行卡 A / B（手动）：[`RUN_CARD.md`](RC_patrol_20261010-1621/RUN_CARD.md)
  - 自动发群代码与说明：[`autopost/`](RC_patrol_20261010-1621/autopost/)（[`README_autopost.md`](RC_patrol_20261010-1621/autopost/README_autopost.md)）
  - 运行记录：[`RUN_LOG.md`](RC_patrol_20261010-1621/RUN_LOG.md)
  - 清单与校验和：[`MANIFEST.md`](RC_patrol_20261010-1621/MANIFEST.md)
- 原始 zip：`RC_patrol_package_20261010-1621.zip`，sha256 见 `RC_patrol_package_20261010-1621.zip.sha256`。
- 相对 07:36 的设置包，新增了：
  - round11 工具包（`replay-test` 离线回放）；白天实查 10/9 21:00 一致（2152 / 1235 / 214 / 152）；历史 7 行（10/3…10/9）。
  - `autopost/`：每晚纽约 22:05 起自动跑运行卡 A 那条命令，自己核对后发飞书群；取不到就发一句固定的话（可重试的失败最晚 23:35 发，核对 / 查询类失败当场发）；同一段不发两次、有人手动跑过就不发。`verify` 4/4，离线测试 56 项 OK，离线演练 OK。
  - 部署指南、运行卡 C。
- 现状：
  - autopost 已在当前运行环境装好，测试群的测试消息 ok。
  - 当前环境是会话式 Docker 容器，没有 cron，过渡期用会话内定时（10-11 起发测试群）。它只在装它的那个 Claude 会话里有效：会话退出即失效，10-17 过期。长期要按部署指南装到常开、有 cron 的机器上。
- 仓库和各包里不含任何飞书 webhook 地址：地址在运行机器的 `_local_only/` 里，`_local_only/` 不打包。
- 隐私扫描：251 个文件，unresolved 0。
- eoHQ 预上线核对（P6）今晚 22:00 后续跑，届时另出最终包。

## 巡检上一版：RC_patrol_20261010-0736（2026-10-10 设置阶段，已被 RC_patrol_20261010-1621 取代）

- 包内容（已解压）：[`RC_patrol_20261010-0736/`](RC_patrol_20261010-0736/)
  - 入口：[`README.md`](RC_patrol_20261010-0736/README.md)
  - 每晚运行卡：[`RUN_CARD.md`](RC_patrol_20261010-0736/RUN_CARD.md)
  - 运行记录：[`RUN_LOG.md`](RC_patrol_20261010-0736/RUN_LOG.md)
  - 给 David 的 Doris 写法：[`doris/`](RC_patrol_20261010-0736/doris/)
  - 清单与校验和：[`MANIFEST.md`](RC_patrol_20261010-0736/MANIFEST.md)
- 原始 zip：`RC_patrol_package_20261010-0736.zip`，sha256 见 `RC_patrol_package_20261010-0736.zip.sha256`。
- 口径：①短信请求总量、②PASS、③非 +1 / 非 +86 的 PASS、④21 个区号的 PASS；窗口为纽约时间 21:00 往前整 24 小时。
- 核对：
  - 纽约日 09-20…09-26 共 7 天，与第三轮包逐格一致；
  - UTC 10-07 和 10-08 与 Doris 差 +0 / +0；
  - 历史已写入 3 个 21:00 窗口。
- **设置阶段的包**：eoHQ 预上线核对（P6）今晚 22:00 后续跑，届时另出最终包。
- 隐私扫描：187 个文件，unresolved 0。

## 数据层最新：RC_data_20261010-0013（2026-10-10，DR-030…038 + 常设项）

- 包内容（已解压）：[`RC_data_20261010-0013/`](RC_data_20261010-0013/) — 入口 [`README.md`](RC_data_20261010-0013/README.md)，DR 结论 [`04_数据问题结论.md`](RC_data_20261010-0013/04_数据问题结论.md)，开放探索 [`05_开放探索_20261009.md`](RC_data_20261010-0013/05_开放探索_20261009.md)，清单与校验和 [`MANIFEST.md`](RC_data_20261010-0013/MANIFEST.md)
- 原始 zip：`RC_data_package_20261010-0013.zip`，sha256 见 `RC_data_package_20261010-0013.zip.sha256`（桌面 D1 用它）
- 窗口：近 7 日 = 纽约日 2026-10-03…10-09；桥接序列 = 纽约日 09-27…10-09；长序列 = 纽约日 06-01…10-09
- DR：22 节（已答复 14、待确认 5、部分答复 2、待取数 1）；DR-002、DR-022 短节（Doris 不可达）；DR-028、DR-029 本次跳过
- 工具包 tk01–tk11（新增 tk11 绕过监控），61/61 项核对一致
- 隐私扫描（`toolkit/privacy_scan.py`）：557 个文件，unresolved 0

## 上一版：RC_data_20260927-0614（2026-09-27，DR-027 专项）

- 包内容（已解压）：[`RC_data_20260927-0614/`](RC_data_20260927-0614/)；zip：`RC_data_package_20260927-0614.zip`（+ `.sha256`）；近 7 日 = 纽约日 2026-09-20…09-26；13 条 DR（已答复 6、待确认 4、部分答复 2、待取数 1；新开 DR-029）；隐私扫描 unresolved 0。

## 第二版：RC_data_20260926-1722（2026-09-26）

- 包内容（已解压）：[`RC_data_20260926-1722/`](RC_data_20260926-1722/)；zip：`RC_data_package_20260926-1722.zip`（+ `.sha256`）；近 7 日 = 纽约日 2026-09-19…09-25；19 条 DR（已答复 12、待确认 5、部分答复 2）；隐私扫描 unresolved 0。

## 第一版：RC_data_20260925-0817（2026-09-25）

- 包内容（已解压）：[`RC_data_20260925-0817/`](RC_data_20260925-0817/)；zip：`RC_data_package_20260925-0817.zip`（+ `.sha256`）；隐私扫描 unresolved 0。
