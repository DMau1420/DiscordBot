"# DiscordBot" 
Ingresa la ip de tu servidor
Dependiendo si es linux o windows cambia la extencion de run.bat o run.sh
En la carpeta McServer crea tu servidor de minecraft
Dentro de ServerBot.py ingresa tu token de discord y tu ip si cuentas con un dominio ponlo ahi 
aqui puedes obtener tu token https://discord.com/developers
Es necesario usar un proveedor de servicios tcp/ip como playit o ngrok, ebido a que usa la libreria mcstatus y esta comprueba por red que el servidor este activo
en caso de no usar un servicio tcp/ip y usarlo de manera local abre puerto 25655 (puerto default de minecraft)
