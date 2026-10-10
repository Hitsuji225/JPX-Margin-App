import os, re, sys, subprocess, tempfile, threading, queue, unicodedata
from pathlib import Path
from urllib.parse import urljoin
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup

INDEX='https://www.jpx.co.jp/markets/statistics-equities/margin/01.html'
HEADERS={'User-Agent':'Mozilla/5.0'}
LABELS=['売残合計','売残合計 前日比','買残合計','買残合計 前日比','一般信用 売残','一般信用 売残 前日比','制度信用 売残','制度信用 売残 前日比','一般信用 買残','一般信用 買残 前日比','制度信用 買残','制度信用 買残 前日比']
def norm(s): return unicodedata.normalize('NFKC',s).replace(' ','').casefold()
def num(s): return int(s.replace(',','').replace('▲','-').replace(' ',''))
def pdf_tool():
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    tool=base/'poppler'/'pdftotext.exe'
    return str(tool) if tool.exists() else 'pdftotext'
def parse_pdf(data):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'source.pdf';path.write_bytes(data)
        proc=subprocess.run(
    [pdf_tool(), '-layout', str(path), '-'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False
)
if proc.returncode != 0:
    raise RuntimeError(
        f"PDF変換エラー（終了コード: {proc.returncode}）\n"
        f"詳細: {proc.stderr.decode('utf-8', errors='replace')}"
    )
    content=proc.stdout.decode('utf-8',errors='replace')
    date=re.search(r'(20\d\d/\d\d?/\d\d?)\s+申込み現在',content)
    rows=[]
    for page,body in enumerate(content.split('\f'),1):
        for line in body.splitlines():
            if '株数 Shs.' not in line:continue
            left,right=line.split('株数 Shs.',1)
            m=re.search(r'(?<![A-Z0-9])([0-9]{3}[0-9A-Z]0)\s+([A-Z]{2}[A-Z0-9]{10})\s*$',left)
            if not m:continue
            fields=re.findall(r'▲\s*[\d,]+|(?<![\w.])[\d,]+(?:\.\d+%)?|\*',right)
            if len(fields)!=14:continue
            try: vals=[num(fields[i]) for i in [0,1,3,4,6,7,8,9,10,11,12,13]]
            except ValueError:continue
            name=re.sub(r'^\s*[ABCFJKMT]\s+','',left[:m.start()].strip())
            name=re.split(r'\s{2,}',name)[0].strip()
            name=re.sub(r'\s+(普通株式|受益証券)$','',name)
            rows.append({'code':m.group(1),'name':name,'page':page,'values':vals})
         return rows,date.group(1) if date else '不明'
def get_latest():
    r=requests.get(INDEX,headers=HEADERS,timeout=25);r.raise_for_status()
    soup=BeautifulSoup(r.content,'html.parser')
    urls=[urljoin(INDEX,a['href']) for a in soup.select('a[href]') if re.search(r'\d{8}_mtall\.pdf(?:\?|$)',urljoin(INDEX,a['href']),re.I)]
    if not urls:raise RuntimeError('JPXのPDFリンクが見つかりません。公開ページの変更が考えられます。')
    url=max(urls,key=lambda x:re.search(r'(\d{8})_mtall\.pdf',x,re.I).group(1))
    pdf=requests.get(url,headers=HEADERS,timeout=90);pdf.raise_for_status()
    if not pdf.content.startswith(b'%PDF'):raise RuntimeError('PDF以外のデータが返されました。')
    return pdf.content,url
class App:
    def __init__(self,root):
        self.root=root;root.title('JPX 信用取引残高検索');root.geometry('840x650')
        top=ttk.Frame(root,padding=16);top.pack(fill='x')
        ttk.Label(top,text='JPX 銘柄別信用取引残高',font=('',18,'bold')).pack(anchor='w')
        ttk.Label(top,text='証券コード（6506 / 65060）または銘柄名で検索').pack(anchor='w',pady=(10,4))
        row=ttk.Frame(top);row.pack(fill='x')
        self.query=tk.StringVar(value='6506');ttk.Entry(row,textvariable=self.query,width=36).pack(side='left',fill='x',expand=True)
        self.btn=ttk.Button(row,text='最新データを取得して検索',command=self.search);self.btn.pack(side='left',padx=8)
        self.status=tk.StringVar(value='検索ボタンを押すとJPXから最新PDFを取得します。')
        ttk.Label(top,textvariable=self.status,wraplength=800).pack(anchor='w',pady=8)
        self.results=ttk.Treeview(root,columns=('item','value'),show='headings',height=15)
        self.results.heading('item',text='項目');self.results.heading('value',text='株数 / 前日比')
        self.results.column('item',width=370);self.results.column('value',width=250,anchor='e')
        self.results.pack(fill='both',expand=True,padx=16,pady=8)
        self.meta=tk.StringVar(value='※ JPX公開資料に基づく参考表示。公式PDFとの照合を推奨します。')
        ttk.Label(root,textvariable=self.meta,wraplength=800).pack(fill='x',padx=16,pady=(0,16))
        self.q=queue.Queue();root.after(100,self.poll)
    def search(self):
        self.btn.config(state='disabled');self.status.set('最新のPDFを取得・解析しています…')
        threading.Thread(target=self.worker,args=(self.query.get(),),daemon=True).start()
    def worker(self,query):
        try:
            pdf,url=get_latest();rows,date=parse_pdf(pdf)
            if len(rows)<1000:raise RuntimeError(f'読み取り件数が不足しています（{len(rows)}件）。誤表示を防ぐため中止しました。')
            q=norm(query);matches=[r for r in rows if q in norm(r['name']) or q==r['code'] or (len(q)==4 and r['code']==q+'0')]
            self.q.put(('ok',matches,date,url,len(rows)))
        except Exception as e:self.q.put(('err',str(e)))
    def poll(self):
        try:
            while True:
                result=self.q.get_nowait();self.btn.config(state='normal')
                if result[0]=='err':self.status.set('取得に失敗しました');messagebox.showerror('エラー',result[1]);continue
                _,matches,date,url,count=result
                for i in self.results.get_children():self.results.delete(i)
                if not matches:self.status.set('該当銘柄がありません。');continue
                self.status.set(f'申込日 {date} / 読取銘柄数 {count:,} / 該当 {len(matches)}件')
                for r in matches[:20]:
                    self.results.insert('', 'end',values=(f"【{r['name']}（{r['code']}）】",f"PDF {r['page']}ページ"))
                    for label,val in zip(LABELS,r['values']):
                        self.results.insert('', 'end',values=(label,f'{val:+,}' if '前日比' in label else f'{val:,}'))
                self.meta.set(f'原本: {url}　※ 合計と内訳の整合を公式PDFでご確認ください。')
        except queue.Empty:pass
        self.root.after(100,self.poll)
if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
