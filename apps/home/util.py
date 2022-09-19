from flask import render_template, request, flash, url_for, session, redirect, url_for

def output_flash_msg():
    if session.get("flash_msg"):
        flash(session.get("flash_msg")["msg"], session.get("flash_msg")["type"])
        session.pop("flash_msg")