import streamlit as st
import os
import time
import json
from pathlib import Path
import wave
import pyaudio
from pydub import AudioSegment
from audiorecorder import audiorecorder
import numpy as np
from scipy.io.wavfile import write
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
import constants as ct

def record_audio(audio_input_file_path):
    """
    音声入力を受け取って音声ファイルを作成
    """
    audio = audiorecorder(
        start_prompt="発話開始",
        pause_prompt="やり直す",
        stop_prompt="発話終了",
        start_style={"color":"white", "background-color":"black"},
        pause_style={"color":"gray", "background-color":"white"},
        stop_style={"color":"white", "background-color":"black"}
    )
    if len(audio) > 0:
        audio.export(audio_input_file_path, format="wav")
    else:
        st.stop()

def transcribe_audio(audio_input_file_path):
    """
    音声入力ファイルから文字起こしテキストを取得
    Args:
        audio_input_file_path: 音声入力ファイルのパス
    """
    with open(audio_input_file_path, 'rb') as audio_input_file:
        transcript = st.session_state.openai_obj.audio.transcriptions.create(
            model="whisper-1",
            file=audio_input_file,
            language="en"
        )
    
    # 音声入力ファイルを削除
    os.remove(audio_input_file_path)
    return transcript

def save_to_wav(llm_response_audio, audio_output_file_path):
    """
    一旦mp3形式で音声ファイル作成後、wav形式に変換
    Args:
        llm_response_audio: LLMからの回答の音声データ
        audio_output_file_path: 出力先のファイルパス
    """
    temp_audio_output_filename = f"{ct.AUDIO_OUTPUT_DIR}/temp_audio_output_{int(time.time())}.mp3"
    with open(temp_audio_output_filename, "wb") as temp_audio_output_file:
        temp_audio_output_file.write(llm_response_audio)
    
    audio_mp3 = AudioSegment.from_file(temp_audio_output_filename, format="mp3")
    audio_mp3.export(audio_output_file_path, format="wav")
    # 音声出力用に一時的に作ったmp3ファイルを削除
    os.remove(temp_audio_output_filename)

def play_wav(audio_output_file_path, speed=1.0):
    """
    音声ファイルの読み上げ
    Args:
        audio_output_file_path: 音声ファイルのパス
        speed: 再生速度（1.0が通常速度、0.5で半分の速さ、2.0で倍速など）
    """
    # 音声ファイルの読み込み
    audio = AudioSegment.from_wav(audio_output_file_path)
    
    # 速度を変更
    if speed != 1.0:
        # frame_rateを変更することで速度を調整
        modified_audio = audio._spawn(
            audio.raw_data, 
            overrides={"frame_rate": int(audio.frame_rate * speed)}
        )
        # 元のframe_rateに戻すことで正常再生させる（ピッチを保持したまま速度だけ変更）
        modified_audio = modified_audio.set_frame_rate(audio.frame_rate)
        modified_audio.export(audio_output_file_path, format="wav")
    # PyAudioで再生
    with wave.open(audio_output_file_path, 'rb') as play_target_file:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(play_target_file.getsampwidth()),
            channels=play_target_file.getnchannels(),
            rate=play_target_file.getframerate(),
            output=True
        )
        data = play_target_file.readframes(1024)
        while data:
            stream.write(data)
            data = play_target_file.readframes(1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    # LLMからの回答の音声ファイルを削除
    os.remove(audio_output_file_path)

def create_chain(system_template):
    """
    LLMによる回答生成用のChain作成
    """
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_template),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}")
    ])
    chain = ConversationChain(
        llm=st.session_state.llm,
        memory=st.session_state.memory,
        prompt=prompt
    )
    return chain

def create_problem_and_play_audio():
    """
    問題生成と音声ファイルの再生
    Args:
        chain: 問題文生成用のChain
        speed: 再生速度（1.0が通常速度、0.5で半分の速さ、2.0で倍速など）
        openai_obj: OpenAIのオブジェクト
    """
    # 問題文を生成するChainを実行し、問題文を取得
    problem = st.session_state.chain_create_problem.predict(input="")
    # LLMからの回答を音声データに変換
    llm_response_audio = st.session_state.openai_obj.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=problem
    )
    # 音声ファイルの作成
    audio_output_file_path = f"{ct.AUDIO_OUTPUT_DIR}/audio_output_{int(time.time())}.wav"
    save_to_wav(llm_response_audio.content, audio_output_file_path)
    # 音声ファイルの読み上げ
    play_wav(audio_output_file_path, st.session_state.speed)
    return problem, llm_response_audio

def create_evaluation():
    """
    ユーザー入力値の評価生成
    """
    llm_response_evaluation = st.session_state.chain_evaluation.predict(input="")
    return llm_response_evaluation

# 以下、新しく追加する機能

def get_level_specific_template(level, theme="一般会話"):
    """
    英語レベルに応じたシステムプロンプトを取得
    Args:
        level: 英語レベル（初級者、中級者、上級者）
        theme: 会話テーマ
    """
    if level == "初級者":
        return ct.SYSTEM_TEMPLATE_BEGINNER.format(theme=theme)
    elif level == "中級者":
        return ct.SYSTEM_TEMPLATE_INTERMEDIATE.format(theme=theme)
    elif level == "上級者":
        return ct.SYSTEM_TEMPLATE_ADVANCED.format(theme=theme)
    else:
        return ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION

def get_level_specific_problem_template(level, theme="一般会話"):
    """
    英語レベルに応じた問題生成プロンプトを取得
    Args:
        level: 英語レベル（初級者、中級者、上級者）
        theme: 会話テーマ
    """
    if level == "初級者":
        return ct.SYSTEM_TEMPLATE_CREATE_PROBLEM_BEGINNER.format(theme=theme)
    elif level == "中級者":
        return ct.SYSTEM_TEMPLATE_CREATE_PROBLEM_INTERMEDIATE.format(theme=theme)
    elif level == "上級者":
        return ct.SYSTEM_TEMPLATE_CREATE_PROBLEM_ADVANCED.format(theme=theme)
    else:
        return ct.SYSTEM_TEMPLATE_CREATE_PROBLEM

def create_level_appropriate_problem_and_play_audio(level, theme="一般会話"):
    """
    レベルに応じた問題文生成と音声ファイルの再生
    Args:
        level: 英語レベル（初級者、中級者、上級者）
        theme: 会話テーマ
    """
    # レベル別のテンプレートを取得
    template = get_level_specific_problem_template(level, theme)
    
    # 問題生成用のチェインを作成
    st.session_state.chain_create_problem = create_chain(template)
    
    # 問題文を生成して音声再生
    return create_problem_and_play_audio()

def create_enhanced_evaluation(level):
    """
    強化されたフィードバックの生成
    Args:
        level: 英語レベル（初級者、中級者、上級者）
    """
    # 強化されたフィードバックテンプレートを使用
    system_template = ct.SYSTEM_TEMPLATE_ENHANCED_EVALUATION.format(
        llm_text=st.session_state.problem,
        user_text=st.session_state.last_user_input,
        level=level
    )
    
    # 評価チェインを作成
    st.session_state.chain_evaluation = create_chain(system_template)
    
    # 評価の生成
    return st.session_state.chain_evaluation.predict(input="")

def provide_cultural_context(sentence):
    """
    文化的コンテキストの提供
    Args:
        sentence: 文脈を解説する対象の文
    """
    # 文化的コンテキスト用のテンプレート
    system_template = ct.SYSTEM_TEMPLATE_CULTURAL_CONTEXT.format(sentence=sentence)
    
    # 一時的なチェインを作成
    cultural_chain = create_chain(system_template)
    
    # 文化的コンテキストの生成
    return cultural_chain.predict(input="")

def analyze_user_errors(conversation_history):
    """
    ユーザーのエラーパターン分析
    Args:
        conversation_history: 会話履歴（最新の5-10回分の会話）
    """
    # エラーパターン分析用のテンプレート
    system_template = ct.SYSTEM_TEMPLATE_ERROR_ANALYSIS.format(
        conversation_history=conversation_history
    )
    
    # 一時的なチェインを作成
    analysis_chain = create_chain(system_template)
    
    # エラー分析の生成
    return analysis_chain.predict(input="")

def save_conversation_history(user_input, ai_response, evaluation=None):
    """
    会話履歴を保存する
    Args:
        user_input: ユーザーの入力
        ai_response: AIの応答
        evaluation: 評価情報（オプション）
    """
    history_path = 'conversation_history.json'
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 新しいエントリ
    new_entry = {
        "timestamp": timestamp,
        "user_input": user_input,
        "ai_response": ai_response,
        "english_level": st.session_state.englv,
        "mode": st.session_state.mode,
        "theme": st.session_state.get("theme", "一般会話"),
    }
    
    if evaluation:
        new_entry["evaluation"] = evaluation
    
    # 既存の履歴がある場合は読み込み、なければ新規作成
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except:
                history = {"conversations": []}
    else:
        history = {"conversations": []}
    
    # 履歴に追加
    history["conversations"].append(new_entry)
    
    # 履歴の保存
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_recent_conversation_history(num_entries=5):
    """
    最近の会話履歴を取得する
    Args:
        num_entries: 取得するエントリ数
    """
    history_path = 'conversation_history.json'
    
    if not os.path.exists(history_path):
        return []
    
    with open(history_path, 'r', encoding='utf-8') as f:
        try:
            history = json.load(f)
            # 最新の n 件を取得
            return history["conversations"][-num_entries:]
        except:
            return []

def adjust_voice_based_on_content(text, openai_obj):
    """
    文脈に応じた音声特性の調整
    Args:
        text: 応答テキスト
        openai_obj: OpenAIクライアントオブジェクト
    """
    # 感情や文脈を分析
    is_question = "?" in text
    is_excited = "!" in text
    is_formal = any(word in text.lower() for word in ["please", "thank you", "excuse me", "sir", "madam"])
    
    # 音声選択（デフォルトはalloy）
    voice = "alloy"
    
    # 質問や興奮した内容には異なる声を使用
    if is_question:
        voice = "nova"  # より明るく質問に適した声
    elif is_excited:
        voice = "shimmer"  # エネルギッシュな声
    elif is_formal:
        voice = "echo"  # よりフォーマルな印象の声
    
    # 音声生成
    return openai_obj.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text
    )

def analyze_pronunciation(audio_file_path, text):
    """
    発音分析機能
    Args:
        audio_file_path: 音声ファイルのパス
        text: 正解のテキスト
    """
    # OpenAIのWhisperモデルを使用して音声を文字起こし
    with open(audio_file_path, 'rb') as audio_file:
        transcript = st.session_state.openai_obj.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en"
        )
    
    # 発音分析用のプロンプト
    pronunciation_prompt = f"""
    以下の「正解テキスト」と「発話テキスト」を比較し、発音の分析をしてください：
    
    正解テキスト: {text}
    発話テキスト: {transcript.text}
    
    以下の点に注目して日本語で分析してください：
    1. 単語の発音の正確さ
    2. イントネーションやリズムの自然さ
    3. 特に改善すべき音素や単語
    4. 良くできている点
    
    具体的なアドバイスと練習方法も提案してください。
    """
    
    # 一時的なチェインを作成して分析
    analysis_chain = create_chain(pronunciation_prompt)
    
    # 発音分析を生成
    return analysis_chain.predict(input="")