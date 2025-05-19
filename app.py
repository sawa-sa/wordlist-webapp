from flask import Flask, request, render_template
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
import pandas as pd
import csv
import os
import re

app = Flask(__name__)
lemmatizer = WordNetLemmatizer()
BUILTIN_DICTIONARY = {}

# 組み込み辞書の読み込み
def load_builtin_dictionary():
    global BUILTIN_DICTIONARY
    path = "data/target1900.xlsx"
    df = pd.read_excel(path, engine="openpyxl")
    for _, row in df.iterrows():
        word = str(row.get("単語", "")).strip().lower()
        meaning = str(row.get("日本語", "")).strip()
        usage = str(row.get("語法", "")).strip() if "語法" in df.columns else ""
        if word and meaning:
            BUILTIN_DICTIONARY[word] = {
                "meaning": meaning,
                "usage": usage if usage.lower() != "nan" else ""
            }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        text = request.form["text"]
        file = request.files.get("wordlist")
        filetype = request.form.get("filetype", "").lower()
        dictionary = {}

        try:
            if file and filetype == "xlsx":
                df = pd.read_excel(file, engine="openpyxl")
                for _, row in df.iterrows():
                    word = str(row.get("単語", "")).strip().lower()
                    meaning = str(row.get("日本語", "")).strip()
                    usage = str(row.get("語法", "")).strip() if "語法" in df.columns else ""
                    if word and meaning:
                        dictionary[word] = {
                            "meaning": meaning,
                            "usage": usage if usage.lower() != "nan" else ""
                        }
            elif file and filetype == "csv":
                reader = csv.reader(file.stream.read().decode("utf-8").splitlines())
                for row in reader:
                    if len(row) >= 2:
                        word = row[0].strip().lower()
                        dictionary[word] = {"meaning": row[1].strip(), "usage": ""}
            elif file and filetype == "txt":
                lines = file.read().decode("utf-8").splitlines()
                for line in lines:
                    if "\t" in line:
                        parts = line.strip().split("\t", 1)
                        if len(parts) == 2:
                            word = parts[0].strip().lower()
                            dictionary[word] = {"meaning": parts[1].strip(), "usage": ""}
            else:
                dictionary = BUILTIN_DICTIONARY.copy()
        except Exception as e:
            return f"辞書読み込みエラー: {e}", 400

        # 簡易トークン化（英単語のみ抽出）
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

        # 各語に対して全品詞からの原型を取得
        lemmatized_set = set()
        for word in words:
            for pos in [wordnet.NOUN, wordnet.VERB, wordnet.ADJ, wordnet.ADV]:
                lemma = lemmatizer.lemmatize(word, pos=pos)
                lemmatized_set.add(lemma)

        # 照合（辞書にある単語だけ、重複なし）
        matched = []
        for lemma in sorted(lemmatized_set):
            if lemma in dictionary:
                entry = dictionary[lemma]
                matched.append((lemma, entry["meaning"], entry["usage"]))

        # .txt 出力
        output_path = os.path.join("static", "temp_output.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("【長文単語リスト】\n")
            f.write("単語\t意味\t語法\n")
            for word, meaning, usage in matched:
                f.write(f"{word}\t{meaning}\t{usage}\n")

        return render_template("result.html", results=matched, txt_path="/static/temp_output.txt")

    return render_template("index.html")

if __name__ == "__main__":
    load_builtin_dictionary()
    app.run(host="0.0.0.0", port=10000)
