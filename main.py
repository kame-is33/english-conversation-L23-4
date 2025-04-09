import streamlit as st
import os
import time
from time import sleep
from pathlib import Path
from streamlit.components.v1 import html
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from openai import OpenAI
from langchain_openai import ChatOpenAI
import functions as ft
import constants as ct

# 各種設定
st.set_page_config(
    page_title=ct.APP_NAME,
    layout="wide"
)

# タイトル表示
st.markdown(f"## {ct.APP_NAME}")

# 初期処理
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.start_flg = False
    st.session_state.pre_mode = ""
    st.session_state.shadowing_flg = False
    st.session_state.shadowing_button_flg = False
    st.session_state.shadowing_count = 0
    st.session_state.shadowing_first_flg = True
    st.session_state.shadowing_audio_input_flg = False
    st.session_state.shadowing_evaluation_first_flg = True
    st.session_state.dictation_flg = False
    st.session_state.dictation_button_flg = False
    st.session_state.dictation_count = 0
    st.session_state.dictation_first_flg = True
    st.session_state.dictation_chat_message = ""
    st.session_state.dictation_evaluation_first_flg = True
    st.session_state.chat_open_flg = False
    st.session_state.problem = ""
    st.session_state.theme = "一般会話"
    st.session_state.show_cultural_context = False
    st.session_state.show_error_analysis = False
    st.session_state.last_user_input = ""
    st.session_state.conversation_counter = 0
    
    # 会話履歴保存用の初期ディレクトリ作成
    if not os.path.exists(ct.AUDIO_INPUT_DIR):
        os.makedirs(ct.AUDIO_INPUT_DIR)
    if not os.path.exists(ct.AUDIO_OUTPUT_DIR):
        os.makedirs(ct.AUDIO_OUTPUT_DIR)
    
    # OpenAI API初期化
    st.session_state.openai_obj = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    st.session_state.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
    st.session_state.memory = ConversationSummaryBufferMemory(
        llm=st.session_state.llm,
        max_token_limit=1000,
        return_messages=True
    )
    # モード「日常英会話」用のChain作成
    st.session_state.chain_basic_conversation = ft.create_chain(ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION)

# サイドバーの設定
with st.sidebar:
    st.header("学習設定")
    
    # 会話テーマ選択
    st.session_state.theme = st.selectbox(
        "会話テーマ",
        options=ct.CONVERSATION_THEMES,
        index=0
    )
    
    # 文化的コンテキストの表示設定
    st.session_state.show_cultural_context = st.checkbox("文化的コンテキストを表示", value=False)
    
    # エラー分析の表示設定
    st.session_state.show_error_analysis = st.checkbox("定期的なエラー分析を表示", value=False)
    
    # 会話履歴の表示
    if st.button("会話履歴を分析"):
        recent_history = ft.get_recent_conversation_history()
        if recent_history:
            with st.expander("最近の会話履歴", expanded=True):
                history_text = ""
                for idx, entry in enumerate(recent_history):
                    history_text += f"**会話 {idx+1}**\n"
                    history_text += f"- 日時: {entry['timestamp']}\n"
                    history_text += f"- レベル: {entry['english_level']}\n"
                    history_text += f"- モード: {entry['mode']}\n"
                    history_text += f"- テーマ: {entry.get('theme', '一般会話')}\n"
                    history_text += f"- ユーザー: {entry['user_input']}\n"
                    history_text += f"- AI応答: {entry['ai_response']}\n\n"
                st.markdown(history_text)
                
                # エラー分析を表示
                if st.session_state.show_error_analysis:
                    with st.spinner("エラーパターンを分析中..."):
                        history_for_analysis = "\n".join([f"User: {entry['user_input']}\nAI: {entry['ai_response']}" for entry in recent_history])
                        error_analysis = ft.analyze_user_errors(history_for_analysis)
                        st.markdown("### エラーパターン分析")
                        st.info(error_analysis)
        else:
            st.info("会話履歴がまだありません。")

# メイン画面のレイアウト設定
col1, col2, col3, col4 = st.columns([2, 2, 3, 3])
with col1:
    if st.session_state.start_flg:
        st.button("開始", use_container_width=True, type="primary")
    else:
        st.session_state.start_flg = st.button("開始", use_container_width=True, type="primary")
with col2:
    st.session_state.speed = st.selectbox(label="再生速度", options=ct.PLAY_SPEED_OPTION, index=3, label_visibility="collapsed")
with col3:
    st.session_state.mode = st.selectbox(label="モード", options=[ct.MODE_1, ct.MODE_2, ct.MODE_3], label_visibility="collapsed")
    # モードを変更した際の処理
    if st.session_state.mode != st.session_state.pre_mode:
        # 自動でそのモードの処理が実行されないようにする
        st.session_state.start_flg = False
        # 「日常英会話」選択時の初期化処理
        if st.session_state.mode == ct.MODE_1:
            st.session_state.dictation_flg = False
            st.session_state.shadowing_flg = False
        # 「シャドーイング」選択時の初期化処理
        st.session_state.shadowing_count = 0
        if st.session_state.mode == ct.MODE_2:
            st.session_state.dictation_flg = False
        # 「ディクテーション」選択時の初期化処理
        st.session_state.dictation_count = 0
        if st.session_state.mode == ct.MODE_3:
            st.session_state.shadowing_flg = False
        # チャット入力欄を非表示にする
        st.session_state.chat_open_flg = False
    st.session_state.pre_mode = st.session_state.mode
with col4:
    st.session_state.englv = st.selectbox(label="英語レベル", options=ct.ENGLISH_LEVEL_OPTION, label_visibility="collapsed")

with st.chat_message("assistant", avatar="images/ai_icon.jpg"):
    st.markdown("こちらは生成AIによる音声英会話の練習アプリです。何度も繰り返し練習し、英語力をアップさせましょう。")
    st.markdown("**【操作説明】**")
    st.success("""
    - モードと再生速度を選択し、「英会話開始」ボタンを押して英会話を始めましょう。
    - モードは「日常英会話」「シャドーイング」「ディクテーション」から選べます。
    - 発話後、5秒間沈黙することで音声入力が完了します。
    - 「一時中断」ボタンを押すことで、英会話を一時中断できます。
    - サイドバーから会話テーマを選択できます。
    """)
st.divider()

# メッセージリストの一覧表示
for message in st.session_state.messages:
    if message["role"] == "assistant":
        with st.chat_message(message["role"], avatar="images/ai_icon.jpg"):
            st.markdown(message["content"])
            # 文化的コンテキストの表示が有効で、アシスタントのメッセージに英文が含まれている場合
            if st.session_state.show_cultural_context and "cultural_context" in message:
                with st.expander("文化的コンテキスト"):
                    st.info(message["cultural_context"])
    elif message["role"] == "user":
        with st.chat_message(message["role"], avatar="images/user_icon.jpg"):
            st.markdown(message["content"])
    else:
        st.divider()

# LLMレスポンスの下部にモード実行のボタン表示
if st.session_state.shadowing_flg:
    st.session_state.shadowing_button_flg = st.button("シャドーイング開始")
if st.session_state.dictation_flg:
    st.session_state.dictation_button_flg = st.button("ディクテーション開始")

# 「ディクテーション」モードのチャット入力受付時に実行
if st.session_state.chat_open_flg:
    st.info("AIが読み上げた音声を、画面下部のチャット欄からそのまま入力・送信してください。")
st.session_state.dictation_chat_message = st.chat_input("※「ディクテーション」選択時以外は送信不可")
if st.session_state.dictation_chat_message and not st.session_state.chat_open_flg:
    st.stop()

# 「英会話開始」ボタンが押された場合の処理
if st.session_state.start_flg:
    # モード：「ディクテーション」
    # 「ディクテーション」ボタン押下時か、「英会話開始」ボタン押下時か、チャット送信時
    if st.session_state.mode == ct.MODE_3 and (st.session_state.dictation_button_flg or st.session_state.dictation_count == 0 or st.session_state.dictation_chat_message):
        if st.session_state.dictation_first_flg:
            # レベルと会話テーマに応じた問題生成テンプレートを使用
            template = ft.get_level_specific_problem_template(st.session_state.englv, st.session_state.theme)
            st.session_state.chain_create_problem = ft.create_chain(template)
            st.session_state.dictation_first_flg = False
        
        # チャット入力以外
        if not st.session_state.chat_open_flg:
            with st.spinner('問題文生成中...'):
                st.session_state.problem, llm_response_audio = ft.create_problem_and_play_audio()
            st.session_state.chat_open_flg = True
            st.session_state.dictation_flg = False
            st.rerun()
        # チャット入力時の処理
        else:
            # チャット欄から入力された場合にのみ評価処理が実行されるようにする
            if not st.session_state.dictation_chat_message:
                st.stop()
            
            # AIメッセージとユーザーメッセージの画面表示
            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(st.session_state.problem)
                
                # 文化的コンテキストの表示が有効な場合
                if st.session_state.show_cultural_context:
                    with st.spinner("文化的コンテキストを取得中..."):
                        cultural_context = ft.provide_cultural_context(st.session_state.problem)
                        with st.expander("文化的コンテキスト"):
                            st.info(cultural_context)
            
            with st.chat_message("user", avatar=ct.USER_ICON_PATH):
                st.markdown(st.session_state.dictation_chat_message)
            
            # 最後のユーザー入力を保存
            st.session_state.last_user_input = st.session_state.dictation_chat_message
            
            # LLMが生成した問題文とチャット入力値をメッセージリストに追加
            cultural_context_data = None
            if st.session_state.show_cultural_context:
                cultural_context_data = cultural_context
                
            st.session_state.messages.append({
                "role": "assistant", 
                "content": st.session_state.problem,
                "cultural_context": cultural_context_data if cultural_context_data else None
            })
            st.session_state.messages.append({"role": "user", "content": st.session_state.dictation_chat_message})
            
            with st.spinner('評価結果の生成中...'):
                if st.session_state.dictation_evaluation_first_flg:
                    # 強化されたフィードバックを使用
                    system_template = ct.SYSTEM_TEMPLATE_ENHANCED_EVALUATION.format(
                        llm_text=st.session_state.problem,
                        user_text=st.session_state.dictation_chat_message,
                        level=st.session_state.englv
                    )
                    st.session_state.chain_evaluation = ft.create_chain(system_template)
                    st.session_state.dictation_evaluation_first_flg = False
                
                # 問題文と回答を比較し、評価結果の生成を指示するプロンプトを作成
                llm_response_evaluation = ft.create_evaluation()
            
            # 評価結果のメッセージリストへの追加と表示
            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(llm_response_evaluation)
            st.session_state.messages.append({"role": "assistant", "content": llm_response_evaluation})
            st.session_state.messages.append({"role": "other"})
            
            # 会話履歴を保存
            ft.save_conversation_history(
                st.session_state.dictation_chat_message, 
                st.session_state.problem, 
                llm_response_evaluation
            )
            
            # 各種フラグの更新
            st.session_state.dictation_flg = True
            st.session_state.dictation_chat_message = ""
            st.session_state.dictation_count += 1
            st.session_state.chat_open_flg = False
            st.rerun()
    
    # モード：「日常英会話」
    if st.session_state.mode == ct.MODE_1:
        # 英語レベルに応じたシステムプロンプトを取得して会話チェインを更新
        level_template = ft.get_level_specific_template(st.session_state.englv, st.session_state.theme)
        st.session_state.chain_basic_conversation = ft.create_chain(level_template)
        
        # 音声入力を受け取って音声ファイルを作成
        audio_input_file_path = f"{ct.AUDIO_INPUT_DIR}/audio_input_{int(time.time())}.wav"
        ft.record_audio(audio_input_file_path)
        
        # 音声入力ファイルから文字起こしテキストを取得
        with st.spinner('音声入力をテキストに変換中...'):
            transcript = ft.transcribe_audio(audio_input_file_path)
            audio_input_text = transcript.text
            
            # 最後のユーザー入力を保存
            st.session_state.last_user_input = audio_input_text
        
        # 音声入力テキストの画面表示
        with st.chat_message("user", avatar=ct.USER_ICON_PATH):
            st.markdown(audio_input_text)
        
        with st.spinner("回答の音声読み上げ準備中..."):
            # ユーザー入力値をLLMに渡して回答取得
            llm_response = st.session_state.chain_basic_conversation.predict(input=audio_input_text)
            
            # 文化的コンテキストを取得（有効な場合）
            cultural_context_data = None
            if st.session_state.show_cultural_context:
                with st.spinner("文化的コンテキストを取得中..."):
                    cultural_context_data = ft.provide_cultural_context(llm_response)
            
            # 文脈に応じて声を選択する機能を使用
            llm_response_audio = ft.adjust_voice_based_on_content(llm_response, st.session_state.openai_obj)
            
            # 一旦mp3形式で音声ファイル作成後、wav形式に変換
            audio_output_file_path = f"{ct.AUDIO_OUTPUT_DIR}/audio_output_{int(time.time())}.wav"
            ft.save_to_wav(llm_response_audio.content, audio_output_file_path)
        
        # 音声ファイルの読み上げ
        ft.play_wav(audio_output_file_path, speed=st.session_state.speed)
        
        # AIメッセージの画面表示とリストへの追加
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(llm_response)
            
            # 文化的コンテキストの表示（有効な場合）
            if st.session_state.show_cultural_context and cultural_context_data:
                with st.expander("文化的コンテキスト"):
                    st.info(cultural_context_data)
        
        # ユーザー入力値とLLMからの回答をメッセージ一覧に追加
        st.session_state.messages.append({"role": "user", "content": audio_input_text})
        st.session_state.messages.append({
            "role": "assistant", 
            "content": llm_response,
            "cultural_context": cultural_context_data if cultural_context_data else None
        })
        
        # 会話履歴を保存
        ft.save_conversation_history(audio_input_text, llm_response)
        
        # 会話カウンターを増やす
        st.session_state.conversation_counter += 1
        
        # 10回の会話ごとにエラー分析を表示（有効な場合）
        if st.session_state.show_error_analysis and st.session_state.conversation_counter % 10 == 0:
            with st.spinner("会話パターンを分析中..."):
                recent_history = ft.get_recent_conversation_history(10)
                if recent_history:
                    history_for_analysis = "\n".join([f"User: {entry['user_input']}\nAI: {entry['ai_response']}" for entry in recent_history])
                    error_analysis = ft.analyze_user_errors(history_for_analysis)
                    with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                        st.markdown("### 会話パターン分析")
                        st.info(error_analysis)
                    st.session_state.messages.append({"role": "assistant", "content": f"### 会話パターン分析\n{error_analysis}"})
                    st.session_state.messages.append({"role": "other"})
    
    # モード：「シャドーイング」
    # 「シャドーイング」ボタン押下時か、「英会話開始」ボタン押下時
    if st.session_state.mode == ct.MODE_2 and (st.session_state.shadowing_button_flg or st.session_state.shadowing_count == 0 or st.session_state.shadowing_audio_input_flg):
        if st.session_state.shadowing_first_flg:
            # レベルと会話テーマに応じた問題生成テンプレートを使用
            template = ft.get_level_specific_problem_template(st.session_state.englv, st.session_state.theme)
            st.session_state.chain_create_problem = ft.create_chain(template)
            st.session_state.shadowing_first_flg = False
        
        if not st.session_state.shadowing_audio_input_flg:
            with st.spinner('問題文生成中...'):
                st.session_state.problem, llm_response_audio = ft.create_level_appropriate_problem_and_play_audio(
                    st.session_state.englv, 
                    st.session_state.theme
                )
                
                # 文化的コンテキストを取得（有効な場合）
                cultural_context_data = None
                if st.session_state.show_cultural_context:
                    with st.spinner("文化的コンテキストを取得中..."):
                        cultural_context_data = ft.provide_cultural_context(st.session_state.problem)
        
        # 音声入力を受け取って音声ファイルを作成
        st.session_state.shadowing_audio_input_flg = True
        audio_input_file_path = f"{ct.AUDIO_INPUT_DIR}/audio_input_{int(time.time())}.wav"
        ft.record_audio(audio_input_file_path)
        st.session_state.shadowing_audio_input_flg = False
        
        with st.spinner('音声入力をテキストに変換中...'):
            # 音声入力ファイルから文字起こしテキストを取得
            transcript = ft.transcribe_audio(audio_input_file_path)
            audio_input_text = transcript.text
            
            # 最後のユーザー入力を保存
            st.session_state.last_user_input = audio_input_text
        
        # AIメッセージとユーザーメッセージの画面表示
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(st.session_state.problem)
            
            # 文化的コンテキストの表示（有効な場合）
            if st.session_state.show_cultural_context and 'cultural_context_data' in locals() and cultural_context_data:
                with st.expander("文化的コンテキスト"):
                    st.info(cultural_context_data)
        
        with st.chat_message("user", avatar=ct.USER_ICON_PATH):
            st.markdown(audio_input_text)
        
        # LLMが生成した問題文と音声入力値をメッセージリストに追加
        st.session_state.messages.append({
            "role": "assistant", 
            "content": st.session_state.problem,
            "cultural_context": cultural_context_data if 'cultural_context_data' in locals() and cultural_context_data else None
        })
        st.session_state.messages.append({"role": "user", "content": audio_input_text})
        
        with st.spinner('評価結果の生成中...'):
            if st.session_state.shadowing_evaluation_first_flg:
                # 強化されたフィードバックを使用
                system_template = ct.SYSTEM_TEMPLATE_ENHANCED_EVALUATION.format(
                    llm_text=st.session_state.problem,
                    user_text=audio_input_text,
                    level=st.session_state.englv
                )
                st.session_state.chain_evaluation = ft.create_chain(system_template)
                st.session_state.shadowing_evaluation_first_flg = False
            
            # 問題文と回答を比較し、評価結果の生成
            llm_response_evaluation = ft.create_evaluation()
        
        # 評価結果のメッセージリストへの追加と表示
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(llm_response_evaluation)
        st.session_state.messages.append({"role": "assistant", "content": llm_response_evaluation})
        st.session_state.messages.append({"role": "other"})
        
        # 会話履歴を保存
        ft.save_conversation_history(
            audio_input_text, 
            st.session_state.problem, 
            llm_response_evaluation
        )
        
        # 各種フラグの更新
        st.session_state.shadowing_flg = True
        st.session_state.shadowing_count += 1
        
        # 「シャドーイング」ボタンを表示するために再描画
        st.rerun()