import requests
import time
import threading
import random
import websocket
from datetime import datetime
from colorama import init, Fore, Back, Style
import psutil

init(autoreset=True)

def print_banner():
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════╗
║          BlockMesh Network AutoBot           ║
║     Github: https://github.com/IM-Hanzou     ║
║      Welcome and do with your own risk!      ║
╚══════════════════════════════════════════════╝
"""
    print(banner)

proxy_tokens = {}
active_threads = []

def get_ip_info(ip_address):
    try:
        response = requests.get(f"https://ipwhois.app/json/{ip_address}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as err:
        print(f"{Fore.RED}Failed to get IP info: {err}")
        return None

def monitor_real_bandwidth():
    old_value = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
    time.sleep(1)
    new_value = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
    bandwidth_mb = (new_value - old_value) / 1024 / 1024
    return bandwidth_mb, bandwidth_mb / 2

def websocket_bandwidth(email, api_token):
    try:
        ws = websocket.WebSocket()
        ws.connect(f"wss://ws.blockmesh.xyz/ws?email={email}&api_token={api_token}")
        print(f"{Fore.GREEN}WebSocket connected for {email}")
        while True:
            ws.send("ping")
            time.sleep(10)
    except Exception as e:
        print(f"{Fore.RED}WebSocket error for {email}: {e}")

def submit_bandwidth(email, api_token, ip_info, proxy_config):
    if not ip_info:
        return
    
    download_speed, upload_speed = monitor_real_bandwidth()
    payload = {
        "email": email,
        "api_token": api_token,
        "download_speed": download_speed,
        "upload_speed": upload_speed,
        "latency": random.uniform(20.0, 300.0),
        "city": ip_info.get("city", "Unknown"),
        "country": ip_info.get("country_code", "XX"),
        "ip": ip_info.get("ip", ""),
        "asn": ip_info.get("asn", "AS0").replace("AS", ""),
        "colo": "Unknown"
    }
    
    try:
        response = requests.post(
            "https://app.blockmesh.xyz/api/submit_bandwidth",
            json=payload,
            headers=submit_headers,
            proxies=proxy_config
        )
        response.raise_for_status()
        print(f"{Fore.GREEN}Bandwidth submitted for {email}: {download_speed:.2f} MB/s down, {upload_speed:.2f} MB/s up")
    except requests.RequestException as err:
        print(f"{Fore.RED}Failed to submit bandwidth for {email}: {err}")

def get_and_submit_task(email, api_token, ip_info, proxy_config):
    if not ip_info:
        return
        
    try:
        response = requests.post(
            "https://app.blockmesh.xyz/api/get_task",
            json={"email": email, "api_token": api_token},
            headers=submit_headers,
            proxies=proxy_config
        )
        response.raise_for_status()
        task_data = response.json()
        
        if not task_data or "id" not in task_data:
            print(f"{Fore.YELLOW}No Task Available for {email}")
            return
            
        task_id = task_data["id"]
        print(f"{Fore.GREEN}Got task for {email}: {task_id}")
        time.sleep(random.randint(60, 120))
        
        submit_url = "https://app.blockmesh.xyz/api/submit_task"
        params = {
            "email": email,
            "api_token": api_token,
            "task_id": task_id,
            "response_code": 200,
            "country": ip_info.get("country_code", "XX"),
            "ip": ip_info.get("ip", ""),
            "asn": ip_info.get("asn", "AS0").replace("AS", ""),
            "colo": "Unknown",
            "response_time": random.uniform(200.0, 600.0)
        }
        
        response = requests.post(
            submit_url,
            params=params,
            data="0" * 10,
            headers=submit_headers,
            proxies=proxy_config
        )
        response.raise_for_status()
        print(f"{Fore.GREEN}Task submitted for {email}: {task_id}")
    except requests.RequestException as err:
        print(f"{Fore.RED}Failed to process task for {email}: {err}")

login_endpoint = "https://api.blockmesh.xyz/api/get_token"
report_endpoint = "https://app.blockmesh.xyz/api/report_uptime?email={email}&api_token={api_token}&ip={ip}"
submit_headers = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "chrome-extension://obfhoiefijlolgdmphcekifedagnkfjp",
    "user-agent": "Mozilla/5.0 (Linux; Ubuntu 20.04) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

def format_proxy(proxy_string):
    if "://" in proxy_string:
        proxy_type, address = proxy_string.split("://")
    else:
        proxy_type = "http"  # Default to http if no protocol is specified
        address = proxy_string
    
    if "@" in address:
        credentials, host_port = address.split("@")
        username, password = credentials.split(":")
        host, port = host_port.split(":")
        proxy_dict = {
            "http": f"{proxy_type}://{username}:{password}@{host}:{port}",
            "https": f"{proxy_type}://{username}:{password}@{host}:{port}"
        }
    else:
        host, port = address.split(":")
        proxy_dict = {
            "http": f"{proxy_type}://{host}:{port}",
            "https": f"{proxy_type}://{host}:{port}"
        }
    return proxy_dict, host

def authenticate(email, password, proxy):
    proxy_config, ip_address = format_proxy(proxy)
    proxy_key = f"{email}:{proxy}"
    
    if proxy_key in proxy_tokens:
        return proxy_tokens[proxy_key], ip_address
        
    login_data = {"email": email, "password": password}
    try:
        response = requests.post(login_endpoint, json=login_data, headers=submit_headers, proxies=proxy_config)
        response.raise_for_status()
        auth_data = response.json()
        api_token = auth_data.get("api_token")
        
        proxy_tokens[proxy_key] = api_token
        print(f"{Fore.GREEN}Login successful for {email} | {ip_address}")
        return api_token, ip_address
    except requests.RequestException as err:
        print(f"{Fore.RED}Login failed for {email} | {ip_address}: {err}")
        return None, None

def send_uptime_report(email, api_token, ip_addr, proxy):
    proxy_config, _ = format_proxy(proxy)
    formatted_url = report_endpoint.format(email=email, api_token=api_token, ip=ip_addr)
    try:
        response = requests.post(formatted_url, headers=submit_headers, proxies=proxy_config)
        response.raise_for_status()
        print(f"{Fore.GREEN}PING successful for {email} | {ip_addr}")
    except requests.RequestException as err:
        print(f"{Fore.RED}Failed to PING for {email} | {ip_addr}: {err}")

def process_proxy_account(email, password, proxy):
    first_run = True
    while True:
        if first_run or f"{email}:{proxy}" not in proxy_tokens:
            api_token, ip_address = authenticate(email, password, proxy)
            first_run = False
        else:
            api_token = proxy_tokens[f"{email}:{proxy}"]
            proxy_config, ip_address = format_proxy(proxy)
        
        if api_token:
            proxy_config, _ = format_proxy(proxy)
            ip_info = get_ip_info(ip_address)
            
            ws_thread = threading.Thread(target=websocket_bandwidth, args=(email, api_token), daemon=True)
            ws_thread.start()
            
            submit_bandwidth(email, api_token, ip_info, proxy_config)
            time.sleep(random.randint(60, 120))
            
            get_and_submit_task(email, api_token, ip_info, proxy_config)
            time.sleep(random.randint(60, 120))
            
            send_uptime_report(email, api_token, ip_address, proxy)
            time.sleep(random.randint(900, 1200))
        
        time.sleep(10)

def get_proxies_from_user():
    proxies = []
    print(f"{Fore.LIGHTBLUE_EX}Enter your proxies (e.g., http://user:pass@host:port or host:port). Type 'done' when finished:")
    while True:
        user_input = input(f"{Fore.LIGHTBLUE_EX}Proxy or 'done': {Style.RESET_ALL}").strip()
        if user_input.lower() == "done":
            break
        if ":" in user_input:
            proxies.append(user_input)
        else:
            print(f"{Fore.RED}Invalid format! Use host:port or http://user:pass@host:port")
    return proxies

def get_accounts_from_user(num_accounts):
    accounts = []
    print(f"{Fore.LIGHTBLUE_EX}Enter {num_accounts} BlockMesh accounts (email:password):")
    for i in range(num_accounts):
        while True:
            user_input = input(f"{Fore.LIGHTBLUE_EX}Account {i+1} (e.g., email:password): {Style.RESET_ALL}").strip()
            if ":" in user_input:
                accounts.append(user_input)
                break
            print(f"{Fore.RED}Invalid format! Use email:password")
    return accounts

def assign_proxies_to_accounts(accounts, proxies, existing_assignments):
    proxy_assignments = existing_assignments.copy()
    available_proxies = [p for p in proxies if p not in [x[2] for x in existing_assignments]]
    num_accounts = len(accounts)
    num_available_proxies = len(available_proxies)
    
    if num_accounts <= num_available_proxies:
        for i in range(num_accounts):
            email, password = accounts[i].split(":", 1)
            proxy = available_proxies[i]
            proxy_assignments.append((email, password, proxy))
        print(f"{Fore.GREEN}[✓] Assigned {num_accounts} new accounts to {num_accounts} proxies (1:1)")
    else:
        print(f"{Fore.YELLOW}Warning: {num_accounts} new accounts > {num_available_proxies} available proxies")
        reuse = input(f"{Fore.LIGHTBLUE_EX}Allow multiple accounts per proxy? (yes/no): {Style.RESET_ALL}").lower()
        if reuse == "yes":
            all_proxies = proxies * ((num_accounts + len(existing_assignments) - 1) // len(proxies) + 1)
            for i in range(num_accounts):
                email, password = accounts[i].split(":", 1)
                proxy = all_proxies[len(existing_assignments) + i]
                proxy_assignments.append((email, password, proxy))
            print(f"{Fore.GREEN}[✓] Assigned {num_accounts} new accounts to {len(proxies)} proxies (reused)")
        else:
            print(f"{Fore.RED}[×] Not enough proxies. Using only {num_available_proxies} new accounts.")
            for i in range(min(num_accounts, num_available_proxies)):
                email, password = accounts[i].split(":", 1)
                proxy = available_proxies[i]
                proxy_assignments.append((email, password, proxy))
    
    return proxy_assignments

def main():
    print(f"\n{Style.BRIGHT}Starting ...")
    
    proxies = get_proxies_from_user()
    if not proxies:
        print(f"{Fore.RED}[×] No proxies provided!")
        exit()
    print(f"{Fore.GREEN}[✓] Collected {len(proxies)} proxies")
    
    while True:
        try:
            num_accounts = int(input(f"{Fore.LIGHTBLUE_EX}How many accounts to set up? {Style.RESET_ALL}"))
            if num_accounts > 0:
                break
            print(f"{Fore.RED}Please enter a number greater than 0!")
        except ValueError:
            print(f"{Fore.RED}Invalid input! Enter a number.")
    
    initial_accounts = get_accounts_from_user(num_accounts)
    print(f"{Fore.GREEN}[✓] Collected {len(initial_accounts)} initial accounts")
    
    assignments = assign_proxies_to_accounts(initial_accounts, proxies, [])
    
    for email, password, proxy in assignments:
        thread = threading.Thread(target=process_proxy_account, args=(email, password, proxy), daemon=True)
        active_threads.append(thread)
        thread.start()
        time.sleep(1)
    
    print(f"{Fore.LIGHTCYAN_EX}[✓] Started {len(active_threads)} threads...")
    
    while True:
        add_more = input(f"{Fore.LIGHTBLUE_EX}Add more accounts? (yes/no): {Style.RESET_ALL}").lower()
        if add_more != "yes":
            break
        
        while True:
            try:
                num_new_accounts = int(input(f"{Fore.LIGHTBLUE_EX}How many additional accounts? {Style.RESET_ALL}"))
                if num_new_accounts > 0:
                    break
                print(f"{Fore.RED}Please enter a number greater than 0!")
            except ValueError:
                print(f"{Fore.RED}Invalid input! Enter a number.")
        
        new_accounts = get_accounts_from_user(num_new_accounts)
        print(f"{Fore.GREEN}[✓] Collected {len(new_accounts)} additional accounts")
        
        assignments = assign_proxies_to_accounts(new_accounts, proxies, assignments)
        
        existing_pairs = {(email, proxy) for email, _, proxy in active_threads}
        for email, password, proxy in assignments:
            if (email, proxy) not in existing_pairs:
                thread = threading.Thread(target=process_proxy_account, args=(email, password, proxy), daemon=True)
                active_threads.append(thread)
                thread.start()
                time.sleep(1)
        
        print(f"{Fore.LIGHTCYAN_EX}[✓] Now running {len(active_threads)} threads...")
    
    print(f"{Fore.LIGHTCYAN_EX}Running {len(active_threads)} threads. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Stopping ...")

if __name__ == "__main__":
    print_banner()
    try:
        main()
    except Exception as e:
        print(f"{Fore.RED}An error occurred: {str(e)}")
