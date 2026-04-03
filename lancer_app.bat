@echo off
echo ================================================
echo   Running Cockpit - Lancement de l'application
echo ================================================
echo.
echo L'app va s'ouvrir dans ton navigateur...
echo Pour arreter : ferme cette fenetre ou fais Ctrl+C
echo.
streamlit run app.py --server.headless false
pause
