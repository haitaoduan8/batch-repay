import flet as ft
import requests
import json
import csv
import time
import threading
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
BASE_URL = "https://cs.cjfintech.com/api"

REPAY_TYPES = {
    "merge": "PAYBYOVERDUE",
    "onebyone": "PAYONEBYOVERDUE"
}

PRODUCTS = {
    "11": "哈银",
    "1": "廊坊"
}


class BatchRepayApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "批量还款划扣工具"
        self.page.window.width = 1000
        self.page.window.height = 700
        self.page.padding = 20
        self.page.theme_mode = ft.ThemeMode.DARK
        
        # 数据
        self.loans = []
        self.results = []
        self.token = ""
        self.is_running = False
        
        # 加载保存的 token
        self._load_token()
        
        # UI 组件
        self.token_input = ft.TextField(
            label="Token",
            value=self.token,
            width=500,
            password=True,
            can_reveal_password=True
        )
        
        self.loan_input = ft.TextField(
            label="借据编号:产品ID (多行，每行一条)",
            multiline=True,
            min_lines=3,
            max_lines=6,
            width=500,
            hint_text="504HHDHL...=11\n504HHDHL...=11"
        )
        
        self.repay_type = ft.Dropdown(
            label="还款类型",
            width=200,
            value="merge",
            options=[
                ft.dropdown.Option("merge", "合并还"),
                ft.dropdown.Option("onebyone", "按期还")
            ]
        )
        
        self.progress_bar = ft.ProgressBar(width=600, value=0, visible=False)
        self.progress_text = ft.Text("", size=12, color="grey700")
        
        self.results_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("状态", color="white")),
                ft.DataColumn(ft.Text("借据编号", color="white")),
                ft.DataColumn(ft.Text("产品", color="white")),
                ft.DataColumn(ft.Text("期次", color="white")),
                ft.DataColumn(ft.Text("金额", color="white")),
                ft.DataColumn(ft.Text("原因", color="white"))
            ],
            rows=[],
            border=ft.border.all(1, "#333333"),
            heading_row_color="#1e1e1e"
        )
        
        self.log_text = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=8,
            max_lines=8,
            width=600,
            text_size=11
        )
        
        # 构建界面
        self._build_ui()
    
    def _load_token(self):
        """加载保存的 token"""
        token_file = Path.home() / ".batch_repay_token"
        if token_file.exists():
            try:
                self.token = token_file.read_text(encoding='utf-8').strip()
            except:
                self.token = ""
    
    def _save_token(self, token):
        """保存 token"""
        self.token = token
        token_file = Path.home() / ".batch_repay_token"
        token_file.write_text(token, encoding='utf-8')
    
    def _build_ui(self):
        """构建界面"""
        # Token 区域
        token_row = ft.Row([
            self.token_input,
            ft.ElevatedButton("保存Token", on_click=self._save_token_click, width=100)
        ])
        
        # 输入区域
        input_row = ft.Row([
            self.loan_input,
            ft.Column([
                ft.ElevatedButton("添加", on_click=self._add_loans_click, width=80),
                ft.ElevatedButton("导入CSV", on_click=self._import_csv_click, width=80),
                ft.ElevatedButton("清空", on_click=self._clear_loans_click, width=80)
            ])
        ])
        
        # 控制区域
        control_row = ft.Row([
            self.repay_type,
            ft.ElevatedButton("试算", on_click=self._trial_click, width=80, color="blue"),
            ft.ElevatedButton("划扣", on_click=self._apply_click, width=80, color="green"),
            ft.ElevatedButton("查询", on_click=self._query_click, width=80, color="orange")
        ])
        
        # 进度区域
        progress_col = ft.Column([
            self.progress_bar,
            self.progress_text
        ])
        
        # 结果表格
        results_card = ft.Container(
            content=ft.Column([
                ft.Text("结果", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.ListView(
                    controls=[self.results_table],
                    height=250,
                    spacing=0
                )
            ]),
            padding=15,
            width=950,
            bgcolor="#1e1e1e",
            border_radius=10
        )
        
        # 日志区域
        log_card = ft.Container(
            content=ft.Column([
                ft.Text("操作日志", size=16, weight=ft.FontWeight.BOLD, color="white"),
                self.log_text
            ]),
            padding=15,
            width=950,
            bgcolor="#1e1e1e",
            border_radius=10
        )
        
        # 主布局
        self.page.add(
            ft.Text("批量还款划扣工具", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            token_row,
            ft.Divider(),
            input_row,
            control_row,
            progress_col,
            ft.Divider(),
            results_card,
            log_card
        )
    
    def _log(self, msg):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.log_text.value = (self.log_text.value or "") + line
        self.page.update()
    
    def _update_progress(self, current, total, msg=""):
        """更新进度"""
        if total > 0:
            self.progress_bar.value = current / total
            self.progress_text.value = f"{current}/{total} {msg}"
        else:
            self.progress_bar.value = 0
            self.progress_text.value = ""
        self.page.update()
    
    def _clear_results(self):
        """清空结果"""
        self.results_table.rows.clear()
        self.results = []
        self.page.update()
    
    def _add_result(self, item):
        """添加结果行"""
        status_icons = {
            'trial_ok': '📊',
            'success': '✅',
            'partial': '⚠️',
            'processing': '⏳',
            'submitted': '❓',
            'failed': '❌'
        }
        
        icon = status_icons.get(item.get('status', ''), '❓')
        fid = item.get('funderLoanId', '')
        short_id = fid[:15] + "..." if len(fid) > 15 else fid
        product = PRODUCTS.get(str(item.get('loanProductId', '')), str(item.get('loanProductId', '')))
        amount = f"¥{item.get('amount', 0):.2f}" if item.get('amount') else '-'
        periods = item.get('periods', '-')
        reason = item.get('failReason', item.get('message', ''))
        
        row = ft.DataRow(cells=[
            ft.DataCell(ft.Text(icon, color="white")),
            ft.DataCell(ft.Text(short_id, size=11, color="white")),
            ft.DataCell(ft.Text(product, size=11, color="white")),
            ft.DataCell(ft.Text(str(periods), size=11, color="white")),
            ft.DataCell(ft.Text(amount, size=11, color="white")),
            ft.DataCell(ft.Text(reason, size=11, color="white"))
        ])
        
        self.results_table.rows.append(row)
        self.results.append(item)
        self.page.update()
    
    def _save_token_click(self, e):
        """保存 Token"""
        token = self.token_input.value.strip()
        if token:
            self._save_token(token)
            self._log(f"Token 已保存")
        else:
            self._log("Token 不能为空")
    
    def _add_loans_click(self, e):
        """添加借据"""
        text = self.loan_input.value.strip()
        if not text:
            self._log("请输入借据数据")
            return
        
        added = 0
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 支持 冒号 或 逗号 分隔
            if '=' in line:
                parts = line.split('=')
            elif ',' in line:
                parts = line.split(',')
            else:
                continue
            
            if len(parts) >= 2:
                fid = parts[0].strip()
                pid = parts[1].strip()
                self.loans.append({
                    'funderLoanId': fid,
                    'loanProductId': pid
                })
                added += 1
        
        self.loan_input.value = ""
        self._log(f"已添加 {added} 条借据，共 {len(self.loans)} 条")
        self.page.update()
    
    def _import_csv_click(self, e):
        """导入 CSV"""
        def on_file_result(result: ft.FilePickerResultEvent):
            if result.files and len(result.files) > 0:
                file_path = result.files[0].path
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        added = 0
                        for row in reader:
                            if len(row) >= 2 and row[0].strip():
                                self.loans.append({
                                    'funderLoanId': row[0].strip(),
                                    'loanProductId': row[1].strip()
                                })
                                added += 1
                    self._log(f"从 CSV 导入 {added} 条，共 {len(self.loans)} 条")
                except Exception as ex:
                    self._log(f"导入失败: {ex}")
                self.page.update()
        
        file_picker = ft.FilePicker(on_result=on_file_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files(
            dialog_title="选择 CSV 文件",
            allowed_extensions=["csv", "txt"]
        )
    
    def _clear_loans_click(self, e):
        """清空借据"""
        self.loans.clear()
        self._log("已清空所有借据")
        self.page.update()
    
    def _get_headers(self, loan_product_id):
        """获取请求头"""
        return {
            "Biz-Protocol": "CS",
            "Biz-ClientType": "Website",
            "Biz-ServerEnv": "30001",
            "Biz-MerchantId": "1000001",
            "Biz-UserId": "110",
            "Biz-SessionType": "b",
            "Biz-SessionKey": self.token,
            "Loan-Product-Id": str(loan_product_id),
            "Content-Type": "application/json"
        }
    
    def _api_post(self, path, loan_product_id, data):
        """API POST 请求"""
        url = f"{BASE_URL}{path}?loanProductId={loan_product_id}"
        headers = self._get_headers(loan_product_id)
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def _trial_api(self, fid, pid, repay_type):
        """试算 API"""
        data = {
            "funderLoanId": fid,
            "repayType": repay_type,
            "periods": None,
            "repaymentApplyType": "COLLECTION"
        }
        return self._api_post("/collection/repayTrail", pid, data)
    
    def _apply_api(self, fid, pid, repay_type, amount, periods):
        """划扣 API"""
        data = {
            "funderLoanId": fid,
            "payableTotalAmount": amount,
            "periods": periods,
            "repayType": repay_type
        }
        return self._api_post("/collection/repayApply", pid, data)
    
    def _query_api(self, fid, pid):
        """查询 API"""
        today = datetime.now().strftime("%Y-%m-%d")
        data = {
            "funderLoanId": fid,
            "startTime": today,
            "endTime": today,
            "current": 1,
            "size": 10
        }
        return self._api_post("/collection/queryRepayApplyRecord", pid, data)
    
    def _run_trial(self):
        """执行试算"""
        self.is_running = True
        self._clear_results()
        
        repay_type_code = REPAY_TYPES[self.repay_type.value]
        repay_type_name = "合并还" if self.repay_type.value == "merge" else "按期还"
        
        self._log(f"开始试算，类型: {repay_type_name}，共 {len(self.loans)} 条")
        
        success = 0
        fail = 0
        
        for i, loan in enumerate(self.loans, 1):
            fid = loan['funderLoanId']
            pid = loan['loanProductId']
            
            self._update_progress(i, len(self.loans), f"试算中...")
            
            try:
                resp = self._trial_api(fid, pid, repay_type_code)
                
                if resp.get('code') == 0 and resp.get('data'):
                    data = resp['data']
                    periods = ','.join(str(d['period']) for d in data.get('details', []))
                    
                    item = {
                        'funderLoanId': data.get('funderLoanId', fid),
                        'loanProductId': pid,
                        'repayType': repay_type_code,
                        'periods': periods,
                        'amount': data.get('payableTotalAmount'),
                        'status': 'trial_ok',
                        'failReason': ''
                    }
                    success += 1
                else:
                    item = {
                        'funderLoanId': fid,
                        'loanProductId': pid,
                        'repayType': repay_type_code,
                        'status': 'failed',
                        'amount': None,
                        'periods': None,
                        'failReason': resp.get('msg', '试算失败')
                    }
                    fail += 1
                
                self._add_result(item)
                
            except Exception as ex:
                item = {
                    'funderLoanId': fid,
                    'loanProductId': pid,
                    'repayType': repay_type_code,
                    'status': 'failed',
                    'amount': None,
                    'periods': None,
                    'failReason': str(ex)
                }
                fail += 1
                self._add_result(item)
            
            if i < len(self.loans):
                time.sleep(0.5)
        
        self._update_progress(0, 0)
        self._log(f"试算完成: {success} 成功, {fail} 失败")
        self.is_running = False
    
    def _trial_click(self, e):
        """试算按钮"""
        if self.is_running:
            self._log("正在运行中，请等待...")
            return
        
        if not self.token:
            self._log("请先输入 Token")
            return
        
        if not self.loans:
            self._log("请先添加借据")
            return
        
        threading.Thread(target=self._run_trial, daemon=True).start()
    
    def _run_apply(self):
        """执行划扣"""
        self.is_running = True
        self._clear_results()
        
        repay_type_code = REPAY_TYPES[self.repay_type.value]
        repay_type_name = "合并还" if self.repay_type.value == "merge" else "按期还"
        
        self._log(f"开始划扣，类型: {repay_type_name}，共 {len(self.loans)} 条")
        
        counts = {'success': 0, 'partial': 0, 'processing': 0, 'submitted': 0, 'failed': 0}
        
        for i, loan in enumerate(self.loans, 1):
            fid = loan['funderLoanId']
            pid = loan['loanProductId']
            
            self._update_progress(i, len(self.loans), f"处理中...")
            
            try:
                # 试算
                trial_resp = self._trial_api(fid, pid, repay_type_code)
                
                if trial_resp.get('code') != 0 or not trial_resp.get('data'):
                    item = {
                        'funderLoanId': fid,
                        'loanProductId': pid,
                        'repayType': repay_type_code,
                        'status': 'failed',
                        'amount': None,
                        'periods': None,
                        'failReason': f"试算失败: {trial_resp.get('msg', '未知')}"
                    }
                    counts['failed'] += 1
                    self._add_result(item)
                    continue
                
                trail_data = trial_resp['data']
                amount = trail_data.get('payableTotalAmount')
                periods = ','.join(str(d['period']) for d in trail_data.get('details', []))
                
                # 划扣
                apply_resp = self._apply_api(fid, pid, repay_type_code, amount, periods)
                
                if apply_resp.get('code') != 0:
                    item = {
                        'funderLoanId': fid,
                        'loanProductId': pid,
                        'repayType': repay_type_code,
                        'periods': periods,
                        'amount': amount,
                        'status': 'failed',
                        'failReason': f"提交失败: {apply_resp.get('msg', '未知')}"
                    }
                    counts['failed'] += 1
                    self._add_result(item)
                    continue
                
                # 等待并查询
                self._update_progress(i, len(self.loans), "等待结果...")
                time.sleep(3)
                
                query_resp = self._query_api(fid, pid)
                
                if query_resp.get('code') == 0 and query_resp.get('data', {}).get('records'):
                    record = query_resp['data']['records'][0]
                    repay_state = record.get('repayState', '')
                    fail_reason = record.get('failReason', '')
                    
                    if repay_state == 'SUCCESS':
                        status = 'success'
                    elif repay_state == 'PART_SUCCESS':
                        status = 'partial'
                    elif repay_state == 'ING':
                        status = 'processing'
                    else:
                        status = 'failed'
                    
                    item = {
                        'funderLoanId': fid,
                        'loanProductId': pid,
                        'repayType': repay_type_code,
                        'periods': periods,
                        'amount': amount,
                        'status': status,
                        'failReason': fail_reason
                    }
                else:
                    item = {
                        'funderLoanId': fid,
                        'loanProductId': pid,
                        'repayType': repay_type_code,
                        'periods': periods,
                        'amount': amount,
                        'status': 'submitted',
                        'failReason': '已提交，暂未查到'
                    }
                
                counts[item['status']] += 1
                self._add_result(item)
                
            except Exception as ex:
                item = {
                    'funderLoanId': fid,
                    'loanProductId': pid,
                    'repayType': repay_type_code,
                    'status': 'failed',
                    'amount': None,
                    'periods': None,
                    'failReason': str(ex)
                }
                counts['failed'] += 1
                self._add_result(item)
            
            if i < len(self.loans):
                time.sleep(1)
        
        self._update_progress(0, 0)
        
        result_msg = "划扣完成: "
        for status, count in counts.items():
            if count > 0:
                result_msg += f"{status}={count} "
        self._log(result_msg)
        
        self.is_running = False
    
    def _apply_click(self, e):
        """划扣按钮"""
        if self.is_running:
            self._log("正在运行中，请等待...")
            return
        
        if not self.token:
            self._log("请先输入 Token")
            return
        
        if not self.loans:
            self._log("请先添加借据")
            return
        
        threading.Thread(target=self._run_apply, daemon=True).start()
    
    def _run_query(self):
        """执行查询"""
        self.is_running = True
        self._clear_results()
        
        self._log(f"开始查询今日结果，共 {len(self.loans)} 条")
        
        counts = {'success': 0, 'partial': 0, 'processing': 0, 'submitted': 0, 'failed': 0}
        
        for i, loan in enumerate(self.loans, 1):
            fid = loan['funderLoanId']
            pid = loan['loanProductId']
            
            self._update_progress(i, len(self.loans), f"查询中...")
            
            try:
                query_resp = self._query_api(fid, pid)
                
                if query_resp.get('code') == 0 and query_resp.get('data', {}).get('records'):
                    record = query_resp['data']['records'][0]
                    repay_state = record.get('repayState', '')
                    fail_reason = record.get('failReason', '')
                    
                    if repay_state == 'SUCCESS':
                        status = 'success'
                    elif repay_state == 'PART_SUCCESS':
                        status = 'partial'
                    elif repay_state == 'ING':
                        status = 'processing'
                    else:
                        status = 'failed'
                    
                    item = {
                        'funderLoanId': fid,
                        'loanProductId': pid,
                        'repayType': record.get('repayType', ''),
                        'periods': record.get('periods', ''),
                        'amount': record.get('payableTotalAmount'),
                        'status': status,
                        'failReason': fail_reason
                    }
                else:
                    item = {
                        'funderLoanId': fid,
                        'loanProductId': pid,
                        'repayType': '',
                        'periods': '',
                        'amount': None,
                        'status': 'submitted',
                        'failReason': '未找到记录'
                    }
                
                counts[item['status']] += 1
                self._add_result(item)
                
            except Exception as ex:
                item = {
                    'funderLoanId': fid,
                    'loanProductId': pid,
                    'repayType': '',
                    'periods': '',
                    'amount': None,
                    'status': 'failed',
                    'failReason': str(ex)
                }
                counts['failed'] += 1
                self._add_result(item)
            
            if i < len(self.loans):
                time.sleep(0.3)
        
        self._update_progress(0, 0)
        
        result_msg = "查询完成: "
        for status, count in counts.items():
            if count > 0:
                result_msg += f"{status}={count} "
        self._log(result_msg)
        
        self.is_running = False
    
    def _query_click(self, e):
        """查询按钮"""
        if self.is_running:
            self._log("正在运行中，请等待...")
            return
        
        if not self.token:
            self._log("请先输入 Token")
            return
        
        if not self.loans:
            self._log("请先添加借据")
            return
        
        threading.Thread(target=self._run_query, daemon=True).start()


def main(page: ft.Page):
    BatchRepayApp(page)


if __name__ == "__main__":
    ft.app(target=main)
