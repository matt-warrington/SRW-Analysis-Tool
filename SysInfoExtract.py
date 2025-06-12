import re
import myUtils

def get_key_mapping(language='en'):
    """
    Returns a dictionary mapping localized keys to English ones
    Args:
        language (str): Language code ('en', 'ja', 'es', 'de', 'fr', etc.)
    """
    mappings = {
        'ja': {
            "ホスト名": "Host Name",
            "OS 名": "OS Name",
            "OS バージョン": "OS Version",
            "OS 製造元": "OS Manufacturer",
            "OS 構成": "OS Configuration",
            "OS ビルドの種類": "OS Build Type",
            "登録されている所有者": "Registered Owner",
            "登録されている組織": "Registered Organization",
            "プロダクト ID": "Product ID",
            "最初のインストール日付": "Original Install Date",
            "システム起動時間": "System Boot Time",
            "システム製造元": "System Manufacturer",
            "システム モデル": "System Model",
            "システムの種類": "System Type",
            "プロセッサ": "Processor(s)",
            "BIOS バージョン": "BIOS Version",
            "Windows ディレクトリ": "Windows Directory",
            "システム ディレクトリ": "System Directory",
            "起動デバイス": "Boot Device",
            "システム ロケール": "System Locale",
            "入力ロケール": "Input Locale",
            "タイム ゾーン": "Time Zone",
            "物理メモリの合計": "Total Physical Memory",
            "利用できる物理メモリ": "Available Physical Memory",
            "仮想メモリ: 最大サイズ": "Virtual Memory: Max Size",
            "仮想メモリ: 利用可能": "Virtual Memory: Available",
            "仮想メモリ: 使用中": "Virtual Memory: In Use",
            "ページ ファイルの場所": "Page File Location(s)",
            "ドメイン": "Domain",
            "ログオン サーバー": "Logon Server",
            "ホットフィックス": "Hotfix(s)",
            "ネットワーク カード": "Network Card(s)",
        },
        'pt': {
            "Nome do host": "Host Name",
            "Nome do SO": "OS Name",
            "Versão do SO": "OS Version",
            "Fabricante do SO": "OS Manufacturer",
            "Configuração do SO": "OS Configuration",
            "Tipo de compilação do SO": "OS Build Type",
            "Proprietário registrado": "Registered Owner",
            "Organização registrada": "Registered Organization",
            "ID do produto": "Product ID",
            "Data da instalação original": "Original Install Date",
            "Hora da inicialização do sistema": "System Boot Time",
            "Fabricante do sistema": "System Manufacturer",
            "Modelo do sistema": "System Model",
            "Tipo de sistema": "System Type",
            "Processador(es)": "Processor(s)",
            "Versão do BIOS": "BIOS Version",
            "Diretório do Windows": "Windows Directory",
            "Diretório do sistema": "System Directory",
            "Dispositivo de inicialização": "Boot Device",
            "Local do sistema": "System Locale",
            "Local de entrada": "Input Locale",
            "Fuso horário": "Time Zone",
            "Memória física total": "Total Physical Memory",
            "Memória física disponível": "Available Physical Memory",
            "Memória virtual: Tamanho máximo": "Virtual Memory: Max Size",
            "Memória virtual: Disponível": "Virtual Memory: Available",
            "Memória virtual: Em uso": "Virtual Memory: In Use",
            "Local(is) do arquivo de paginação": "Page File Location(s)",
            "Domínio": "Domain",
            "Servidor de logon": "Logon Server",
            "Hotfix(es)": "Hotfix(s)",
            "Placa(s) de rede": "Network Card(s)",
        },
        'es': {
            "Nombre de host": "Host Name",
            "Nombre del SO": "OS Name",
            "Versión del SO": "OS Version",
            "Fabricante del SO": "OS Manufacturer",
            "Configuración del SO": "OS Configuration",
            "Tipo de compilación del SO": "OS Build Type",
            "Propietario registrado": "Registered Owner",
            "Organización registrada": "Registered Organization",
            "ID de producto": "Product ID",
            "Fecha de instalación original": "Original Install Date",
            "Hora de inicio del sistema": "System Boot Time",
            "Fabricante del sistema": "System Manufacturer",
            "Modelo del sistema": "System Model",
            "Tipo de sistema": "System Type",
            "Procesador(es)": "Processor(s)",
            "Versión del BIOS": "BIOS Version",
            "Directorio de Windows": "Windows Directory",
            "Directorio del sistema": "System Directory",
            "Dispositivo de arranque": "Boot Device",
            "Configuración regional del sistema": "System Locale",
            "Configuración regional de entrada": "Input Locale",
            "Zona horaria": "Time Zone",
            "Memoria física total": "Total Physical Memory",
            "Memoria física disponible": "Available Physical Memory",
            "Memoria virtual: Tamaño máximo": "Virtual Memory: Max Size",
            "Memoria virtual: Disponible": "Virtual Memory: Available",
            "Memoria virtual: En uso": "Virtual Memory: In Use",
            "Ubicación(es) del archivo de paginación": "Page File Location(s)",
            "Dominio": "Domain",
            "Servidor de inicio de sesión": "Logon Server",
            "Revisión(es)": "Hotfix(s)",
            "Tarjeta(s) de red": "Network Card(s)",
        },
        'de': {
            "Hostname": "Host Name",
            "Betriebssystemname": "OS Name",
            "Betriebssystemversion": "OS Version",
            "Betriebssystemhersteller": "OS Manufacturer",
            "Betriebssystemkonfiguration": "OS Configuration",
            "Betriebssystem-Buildtyp": "OS Build Type",
            "Registrierter Besitzer": "Registered Owner",
            "Registrierte Organisation": "Registered Organization",
            "Produkt-ID": "Product ID",
            "Ursprüngliches Installationsdatum": "Original Install Date",
            "Systemstartzeit": "System Boot Time",
            "Systemhersteller": "System Manufacturer",
            "Systemmodell": "System Model",
            "Systemtyp": "System Type",
            "Prozessor(en)": "Processor(s)",
            "BIOS-Version": "BIOS Version",
            "Windows-Verzeichnis": "Windows Directory",
            "Systemverzeichnis": "System Directory",
            "Startgerät": "Boot Device",
            "Systemgebietsschema": "System Locale",
            "Eingabegebietsschema": "Input Locale",
            "Zeitzone": "Time Zone",
            "Physikalischer Speicher gesamt": "Total Physical Memory",
            "Verfügbarer physikalischer Speicher": "Available Physical Memory",
            "Virtueller Speicher: Maximalgröße": "Virtual Memory: Max Size",
            "Virtueller Speicher: Verfügbar": "Virtual Memory: Available",
            "Virtueller Speicher: In Verwendung": "Virtual Memory: In Use",
            "Auslagerungsdateipfad(e)": "Page File Location(s)",
            "Domäne": "Domain",
            "Anmeldeserver": "Logon Server",
            "Hotfix(es)": "Hotfix(s)",
            "Netzwerkkarte(n)": "Network Card(s)",
        },
        'fr': {
            "Nom d'hôte": "Host Name",
            "Nom du système d'exploitation": "OS Name",
            "Version du système d'exploitation": "OS Version",
            "Fabricant du système d'exploitation": "OS Manufacturer",
            "Configuration du système d'exploitation": "OS Configuration",
            "Type de build du système d'exploitation": "OS Build Type",
            "Propriétaire enregistré": "Registered Owner",
            "Organisation enregistrée": "Registered Organization",
            "ID de produit": "Product ID",
            "Date d'installation d'origine": "Original Install Date",
            "Heure de démarrage du système": "System Boot Time",
            "Fabricant du système": "System Manufacturer",
            "Modèle du système": "System Model",
            "Type de système": "System Type",
            "Processeur(s)": "Processor(s)",
            "Version du BIOS": "BIOS Version",
            "Répertoire Windows": "Windows Directory",
            "Répertoire système": "System Directory",
            "Périphérique de démarrage": "Boot Device",
            "Paramètres régionaux du système": "System Locale",
            "Paramètres régionaux d'entrée": "Input Locale",
            "Fuseau horaire": "Time Zone",
            "Mémoire physique totale": "Total Physical Memory",
            "Mémoire physique disponible": "Available Physical Memory",
            "Mémoire virtuelle: Taille maximale": "Virtual Memory: Max Size",
            "Mémoire virtuelle: Disponible": "Virtual Memory: Available",
            "Mémoire virtuelle: Utilisée": "Virtual Memory: In Use",
            "Emplacement(s) du fichier d'échange": "Page File Location(s)",
            "Domaine": "Domain",
            "Serveur de connexion": "Logon Server",
            "Correctif(s)": "Hotfix(s)",
            "Carte(s) réseau": "Network Card(s)",
        }
    }
    
    return mappings.get(language, {})

def extract_sysinfo(text):
    # Detect language from system locale line
    language = 'en'  # default
    if 'ja;' in text:
        language = 'ja'
    elif 'pt-br;' in text:
        language = 'pt'
    elif 'es;' in text:
        language = 'es'
    elif 'de;' in text:
        language = 'de'
    elif 'fr;' in text:
        language = 'fr'
    
    # Initialize dictionary to store all system information
    sysinfo = {}
    key_mapping = get_key_mapping(language)
    
    # Split text into lines and process each line
    lines = text.split('\n')
    current_key = None
    current_network = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Handle standard key-value pairs
        if ':' in line and not line.startswith('['):
            key, value = [x.strip() for x in line.split(':', 1)]
            
            # Try to map localized key to English
            english_key = key_mapping.get(key, key)
            sysinfo[english_key] = value
            current_key = english_key
            continue
        
        # Handle multi-line entries (like Processor(s), Hotfix(s), Network Card(s))
        if line.startswith('['):
            if current_key not in sysinfo:
                sysinfo[current_key] = []
            
            # Handle different multi-line formats
            if current_key == "Network Card(s)":
                if line.startswith('['):
                    current_network = {}
                    sysinfo[current_key].append(current_network)
                else:
                    if ':' in line:
                        subkey, subvalue = [x.strip() for x in line.split(':', 1)]
                        current_network[subkey] = subvalue
            elif current_key in ["Processor(s)", "Hotfix(s)"]:
                sysinfo[current_key].append(line.split(': ', 1)[1] if ': ' in line else line)
        
        # Handle network card details that don't start with '['
        elif current_key == "Network Card(s)" and current_network is not None:
            if '		' in line:  # Note: using tab characters for splitting
                subkey, subvalue = [x.strip() for x in line.split('		', 1)]
                current_network[subkey] = subvalue
            elif '[' in line and ']' in line and ':' in line:  # Handle IP address
                current_network.setdefault('IP address(es)', []).append(line.split(': ', 1)[1])
    
    return sysinfo

if __name__ == "__main__":
    # Example usage
    file_path = myUtils.select_file("Select the System Information file to analyze")
    try:
        with open(file_path, "r", encoding="utf-16", errors="ignore") as f:
            content = f.read()
        sys_info = extract_sysinfo(content)
        myUtils.print_nested_dict(sys_info)
    except Exception as e:
        print(f"Error extracting sysinfo with encoding utf-16: {e}")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            sys_info = extract_sysinfo(content)
            myUtils.print_nested_dict(sys_info)
        except Exception as e:
            print(f"Error extracting sysinfo with encoding utf-8: {e}")
