學習成果分析網（Python Flask 原型）
===================================

一、環境需求
- Python 3.10 或更新版本
- 可使用 Windows、macOS 或 Linux

二、啟動方式（Windows）
1. 解壓縮 learning_outcomes_analysis.zip
2. 開啟該資料夾，在網址列輸入 cmd 後按 Enter，或使用終端機切換至此資料夾。
3. 建立虛擬環境（建議）：
   python -m venv .venv
4. 啟用虛擬環境：
   .venv\Scripts\activate
5. 安裝套件：
   pip install -r requirements.txt
6. 啟動網站：
   python app.py
7. 開啟瀏覽器，進入：
   http://127.0.0.1:5000

macOS / Linux 啟動虛擬環境：
   source .venv/bin/activate

三、測試帳號
教師：
   帳號 teacher
   密碼 teacher123
   身分選擇「教師」

學生：
   帳號 student01
   密碼 student123
   身分選擇「學生」
其他學生：student02、student03；密碼皆為 student123。

四、目前原型功能
- 教師與學生分流登入
- 勾選「記住我」可保持登入最多 30 天；未勾選則使用瀏覽器工作階段 Cookie
- 教師查看學生名單、作業成績、測驗平均答對率、各題答對率及匿名問卷
- 學生查看個人成績、班級測驗平均與各題答對率
- 學生提交匿名課程問卷
- SQLite 儲存資料，首次執行自動建立 learning.db 和示範資料

五、重要安全提醒
- 這是本機展示用原型，不是已完成正式部署的校務系統。
- 正式上線前，請設定長且隨機的 SECRET_KEY，使用 HTTPS，並將 COOKIE_SECURE 設為 1。
- 請更換示範帳號密碼，加入 CSRF 防護、登入限制、管理者建立帳號功能及資料備份。
- 「記住我」使用 Flask 簽章 Session Cookie；正式環境建議改用伺服器端 Session 或具撤銷能力的持續登入 Token。
- 匿名問卷資料表不保存學生 ID 或帳號；但若部署正式環境，仍需檢視伺服器日誌、IP 紀錄及小群體統計造成的間接識別風險。
- 範例成績與測驗資料均為虛構示範資料，請勿視為真實學習結果。

六、資料庫
網站第一次執行時會在專案資料夾自動產生 learning.db。
若要重新建立示範資料，可先停止網站，再刪除 learning.db，重新執行 python app.py。