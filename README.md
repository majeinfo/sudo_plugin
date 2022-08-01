# sudo_plugin

Ce plugin permet à sudo d'enregistrer les commandes de l'utilisateur dans un fichier spécifique à l'utilisateur.

Exemple de mise en oeuvre dans le fichier /etc/sudo.conf :

	Plugin python_io python_plugin.so ModulePath=/opt/user_history.py ClassName=SudoIOPlugin Histfile=~/.sudo_history Prefix=sudo AsComment=True Verbose=False
