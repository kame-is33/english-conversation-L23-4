# 生成AI英会話アプリ

生成AIを活用した英会話練習アプリケーションです。音声入力と出力を使った実践的な英語学習が可能です。

## 機能

このアプリには3つのモードがあります：

1. **日常英会話**：AIと自由に英会話ができます。文法の間違いをさりげなく訂正してくれます。
2. **シャドーイング**：AIが読み上げる英語をまねして発音する練習ができます。
3. **ディクテーション**：AIが読み上げる英語を聞き取って入力する練習ができます。

## 使い方

1. モード（日常英会話・シャドーイング・ディクテーション）を選択
2. 再生速度を選択
3. 英語レベルを選択
4. 「開始」ボタンをクリック
5. 各モードに応じた英語練習を行う

## 技術スタック

- **フロントエンド**: Streamlit
- **バックエンド**: Python 3.11
- **AI機能**: OpenAI API (GPT-4o-mini, Whisper, TTS)
- **音声処理**: PyAudio, pydub

## インストール方法

### 前提条件

- Python 3.11以上
- ffmpeg
- portaudio19-dev（音声処理用）

### セットアップ手順

```bash
# リポジトリをクローン
git clone <リポジトリURL>
cd <リポジトリ名>

# 仮想環境を作成
python -m venv env
source env/bin/activate  # Linux/Mac
# または
# env\Scripts\activate  # Windows

# 依存パッケージをインストール
pip install -r requirements.txt

# Streamlitアプリを実行
streamlit run main.py
```

### 環境変数の設定

Streamlit Cloudにデプロイする場合は、以下の環境変数を設定してください：

- `OPENAI_API_KEY`: OpenAI APIの認証キー

## ライセンス

このプロジェクトは[ライセンス名]のもとで公開されています。詳細はLICENSEファイルをご覧ください。