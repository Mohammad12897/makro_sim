# create test_start.py with:
print("test start"); import time; time.sleep(5)

import importlib, sys
for name in ["streamlit","gradio","httpx","yfinance","pandas"]:
    try:
        importlib.import_module(name)
        print("imported", name, flush=True)
    except Exception as e:
        print("failed", name, e, flush=True)

import streamlit as st
print(">>> MINIMAL START", flush=True)
st.write("hello")

import importlib, sys, time
modules = ["yfinance","gradio","httpx","huggingface_hub","streamlit"]
for m in modules:
    try:
        importlib.import_module(m)
        print("imported", m, flush=True)
    except Exception as e:
        print("failed", m, e, flush=True)
    time.sleep(0.2)
