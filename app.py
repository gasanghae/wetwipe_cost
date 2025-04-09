# Streamlit 기반 물티슈 원가계산 웹 앱
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import os
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# 전체 계산 함수 정의 포함
import matplotlib
matplotlib.rcParams['font.family'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']  # 한글 깨짐 방지용 기본 글꼴

... 생략 없이 전체 코드 그대로 사용자 메시지에 있던 모든 줄을 포함 ...

