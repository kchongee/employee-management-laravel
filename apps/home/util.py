from flask import render_template, request, flash, url_for, session, redirect, url_for

def output_flash_msg():
    if session["flash_msg"]:
        flash(session["flash_msg"]["msg"], session["flash_msg"]["type"])
        session.pop("flash_msg")