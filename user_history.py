import sudo
from typing import Tuple, Dict
import errno
import json
import logging
import pwd


VERSION = 1.0


class SudoIOPlugin(sudo.Plugin):
    def __init__(self, 
                 user_env: Tuple[str, ...], 
                 settings: Tuple[str, ...], 
                 version: str, 
                 user_info: Tuple[str, ...], 
                 plugin_options: Tuple[str]) -> None:
        self.user_env = sudo.options_as_dict(user_env)
        self.user_info = sudo.options_as_dict(user_info)
        self.plugin_options = sudo.options_as_dict(plugin_options)
        self.ttyin_buffer = ""

        # Prise en compte des paramètres issus de /etc/sudo.conf
        self.histfile = self.plugin_options.get('Histfile', '.sudo_history')
        self.histfile = self._canonicalize(self.histfile, self.user_info)
        self.prefix = "# " if 'AsComment' in self.plugin_options else ""
        self.prefix += self.plugin_options.get('Prefix', '')

        # On veut logger sur l'écran de l'utilisateur
        self.logger = logging.getLogger('my_io_plugin')
        self.logger.setLevel(logging.DEBUG if 'Verbose' in self.plugin_options else logging.ERROR)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        self.logger.debug(f"INIT user_env {self.user_env}")
        self.logger.debug(f"INIT user_info {self.user_info}")
        self.logger.debug(f"INIT plugin_options {self.plugin_options}")

    def __del__(self) -> None:
        pass

    def open(self, argv: Tuple[str, ...],
             command_info: Tuple[str, ...]) -> int:
        """Fonction appelée avant l'exécution de la commande souhaitée"""
        self.logger.debug(f"EXEC {' '.join(argv)}")
        self.logger.debug(f"EXEC info {json.dumps(command_info, indent=4)}")
        self._log_history(" ".join(argv))

        # On accepte la commande car elle a été acceptée par la politique courante
        return sudo.RC.ACCEPT

    def log_ttyout(self, buf: str) -> int:
        return sudo.RC.ACCEPT

    def log_ttyin(self, buf: str) -> int:
        # On interdit les flèches car on ne peut (facilement) obtenir la véritable commande
        if ord(buf[0]) == 27:
            return sudo.RC.REJECT

        # On traite le <backspace> pour reconstruire la vraie commande
        if ord(buf[0]) == 127:
            self.ttyin_buffer = self.ttyin_buffer[:-1]
        else:
            self.ttyin_buffer += buf

        if buf == '\r':
            # On a capturé la ligne de commande (même en mode sans echo)
            self._log_history(self.ttyin_buffer)
            self.ttyin_buffer = ""

        return sudo.RC.ACCEPT

    def close(self, exit_status: int, error: int) -> None:
        """Fonction appelée après l'exécution d'une commande autorisée"""
        if error == 0:
            self.logger.debug(f"CLOSE Command returned {exit_status}")
        else:
            error_name = errno.errorcode.get(error, "???")
            self.logger.debug(f"CLOSE Failed to execute, execve returned {error} ({error_name}")

    def _canonicalize(self, filename: str, user_info: Dict[str, str]) -> str:
        user = user_info['user']
        try:
            *_, pw_dir, _ = pwd.getpwnam(user)
            filename = filename.replace("~", pw_dir)
        except KeyError:
            self.logger.error(f"ERROR, user {user} does not exist ?")

        return filename

    def _log_history(self, buffer: str) -> None:
        try:
            with open(self.histfile, "a") as f:
                f.write(self.prefix + ' ' + buffer + "\n")
        except Exception as e:
            self.logger.error(f"Erreur d'écriture dans le fichier {self.histfile}")
            self.logger.error(e)

