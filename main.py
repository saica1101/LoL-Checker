import os
import sys
import subprocess
import winreg
import ctypes
from datetime import datetime
from rich.console import Console
from rich.prompt import Confirm
# from rich.panel import Panel
# from rich.text import Text
# from rich.table import Table, box

console = Console()

def run_command(command, timeout=None):
    """共通のコマンド実行関数"""
    timeout = 10
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            error_message = f"コマンドの実行に失敗しました: {' '.join(command)}\nエラー詳細: {result.stderr.strip()}"
            console.print(f"[bold red]{error_message}[/bold red]")
    except subprocess.TimeoutExpired:
        timeout_message = f"コマンドがタイムアウトしました: {' '.join(command)}"
        console.print(f"[bold red]{timeout_message}[/bold red]")
    except FileNotFoundError:
        not_found_message = f"コマンドが見つかりません: {' '.join(command)}\n必要なツールがインストールされているか確認してください。"
        console.print(f"[bold red]{not_found_message}[/bold red]")
    except Exception as e:
        exception_message = f"予期しないエラーが発生しました: {e}"
        console.print(f"[bold red]{exception_message}[/bold red]")
    return None

def is_admin():
    """現在のプロセスが管理者権限で実行されているか確認"""
    try:
        return os.getuid() == 0
    except AttributeError:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            console.print(f"[bold red]管理者権限の確認中にエラーが発生しました: {e}[/bold red]")
            return False

def restart_as_admin():
    """管理者権限で再実行"""
    if not is_admin():
        console.print("[bold yellow]管理者権限が必要です。このプログラムを管理者として再実行してください。[/bold yellow]")
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        except Exception as e:
            console.print(f"[bold red]管理者権限での再実行に失敗しました: {e}[/bold red]")
            console.print("[bold yellow]手動でプログラムを管理者として再実行してください。[/bold yellow]")
            sys.exit(1)

def disable_hypervisor_launch():
    """仮想化ベースのセキュリティを無効化するためにbcdeditを実行"""
    console.print("[bold cyan]仮想化ベースのセキュリティを無効化するための設定を確認中...[/bold cyan]")
    if Confirm.ask("[bold cyan]bcdedit /set hypervisorlaunchtype off を適用してもよろしいですか？[/bold cyan]"):
        run_command(["bcdedit", "/set", "hypervisorlaunchtype", "off"])
        console.print("[bold green]仮想化ベースのセキュリティを無効化しました。再起動してください。[/bold green]")
    else:
        console.print("[bold yellow]手動で以下のコマンドを実行してください: bcdedit /set hypervisorlaunchtype off[/bold yellow]")

def check_virtualization_based_security():
    console.print("[bold cyan]仮想化ベースのセキュリティの状態を確認しています...[/bold cyan]")
    output = run_command(["powershell", "-Command", "(Get-CimInstance Win32_ComputerSystem).HypervisorPresent"])
    if output and "True" in output:
        console.print("[bold red]仮想化ベースのセキュリティが有効です。[/bold red]")
        disable_hypervisor_launch()
    elif output and "False" in output:
        console.print("[bold green]仮想化ベースのセキュリティは無効です。[/bold green]")
    elif not output:
        console.print("[bold yellow]仮想化ベースのセキュリティの状態を確認できませんでした。[/bold yellow]")

def check_core_isolation():
    console.print("[bold cyan]コア分離の状態を確認しています...[/bold cyan]")
    output = run_command(["reg", "query", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\DeviceGuard", "/v", "EnableVirtualizationBasedSecurity"])
    if output and "0x1" in output:
        console.print("[bold red]コア分離が有効です。[/bold red]")
        console.print("[bold yellow]1. Windows セキュリティを開く\n2. デバイス セキュリティ > コア分離の詳細を選択\n3. メモリ整合性をオフにする[/bold yellow]")
        console.input("[bold yellow]手順を完了したら Enter を押してください...[/bold yellow]")
    elif output and "0x0" in output:
        console.print("[bold green]コア分離は無効です。[/bold green]")
    elif not output:
        console.print("[bold yellow]コア分離の状態を確認できませんでした。[/bold yellow]")

def check_dev_override_enable():
    console.print("[bold cyan]DevOverrideEnable の状態を確認しています...[/bold cyan]")
    reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, "DevOverrideEnable")
            if value == 1:
                if Confirm.ask("[bold cyan]DevOverrideEnable が有効です。無効化しますか？[/bold cyan]"):
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_WRITE) as write_key:
                        winreg.SetValueEx(write_key, "DevOverrideEnable", 0, winreg.REG_DWORD, 0)
                    console.print("[bold green]DevOverrideEnable を無効化しました。[/bold green]")
                else:
                    console.print("[bold yellow]DevOverrideEnable を手動で無効化してください。[/bold yellow]")
            else:
                console.print("[bold green]DevOverrideEnable は無効です。[/bold green]")
    except FileNotFoundError:
        console.print("[bold green]DevOverrideEnable の設定が見つかりませんでした。[/bold green]")
    except PermissionError:
        console.print("[bold red]レジストリへのアクセス権限がありません。管理者として再実行してください。[/bold red]")
    except Exception as e:
        console.print(f"[bold red]予期しないエラーが発生しました: {e}[/bold red]")

def main():
    """メイン関数"""
    console.print("[bold blue]LoL-Checker[/bold blue]", justify="center")
    # tool_title = "LoL-Checker"
    # table = Table(show_header=False, title=tool_title, highlight=True, box=box.ROUNDED, show_lines=True, title_justify="center", expand=True)
    # table.add_column("")
    # table.add_column("")
    # table.add_row("[bold cyan]開発者", "saica94")
    # table.add_row("[bold cyan]ゲーム内名", "貴方を土に植えるわ#SAICA")
    # table.add_row("[bold cyan]バージョン", "1.0.0")
    # console.print(table)

    sections = [
        ("Section1/3", check_virtualization_based_security),
        ("Section2/3", check_core_isolation),
        ("Section3/3", check_dev_override_enable),
    ]
    for section_title, function in sections:
        console.rule(f"[bold red]{section_title}")
        try:
            function()
        except Exception as e:
            console.print(f"[bold red]セクションでエラーが発生しました: {e}[/bold red]")

    console.print("[bold green]すべてのチェックが完了しました。[/bold green]")
    console.rule("")
    if Confirm.ask("[bold cyan]今すぐ再起動しますか？[/bold cyan]"):
        run_command(["shutdown", "/r", "/t", "0"])
    else:
        console.print("[bold yellow]プログラムを終了します。[/bold yellow]")

if __name__ == "__main__":
    if not is_admin():
        restart_as_admin()
    else:
        main()