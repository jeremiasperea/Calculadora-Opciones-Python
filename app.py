import tkinter as tk
from tkinter import ttk,messagebox,filedialog
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from models import Leg,strategy_payoff,strategy_greeks,approximate_breakevens,probability_metrics
from strategies import TEMPLATES

class OptionApp:
    def __init__(self,root):
        self.root=root; root.title("Calculadora PRO — Opciones"); root.geometry("1450x900")
        self.v={k:tk.DoubleVar(value=x) for k,x in {"spot":1000,"iv":.35,"r":.05,"q":0,"days":30,"mult":1,"min":.5,"max":1.5}.items()}
        self.v["points"]=tk.IntVar(value=401); self.widgets=[]; self.build(); self.load_template("Long Call")
    def build(self):
        top=ttk.Frame(self.root,padding=8); top.pack(fill="x")
        box=ttk.LabelFrame(top,text="Mercado"); box.pack(side="left",fill="x",expand=True)
        for i,(name,key) in enumerate([("Spot","spot"),("IV","iv"),("Tasa","r"),("Dividendos","q"),("Días","days"),("Multiplicador","mult")]):
            ttk.Label(box,text=name).grid(row=0,column=2*i); ttk.Entry(box,textvariable=self.v[key],width=9).grid(row=0,column=2*i+1,padx=3)
        ctl=ttk.Frame(top); ctl.pack(side="right")
        ttk.Label(ctl,text="Plantilla").grid(row=0,column=0)
        self.combo=ttk.Combobox(ctl,values=list(TEMPLATES),state="readonly",width=20); self.combo.grid(row=0,column=1); self.combo.set("Long Call")
        ttk.Button(ctl,text="Cargar",command=lambda:self.load_template(self.combo.get())).grid(row=0,column=2)
        ttk.Button(ctl,text="CALCULAR",command=self.calculate).grid(row=0,column=3)
        ttk.Button(ctl,text="EXPORTAR",command=self.export).grid(row=0,column=4)
        pan=ttk.Panedwindow(self.root,orient="horizontal"); pan.pack(fill="both",expand=True,padx=8,pady=8)
        left,right=ttk.Frame(pan),ttk.Frame(pan); pan.add(left,weight=1); pan.add(right,weight=3)
        lf=ttk.LabelFrame(left,text="Strategy Builder — 6 patas"); lf.pack(fill="x")
        for c,h in enumerate(["Tipo","Lado","Cantidad","Strike","Prima"]): ttk.Label(lf,text=h).grid(row=0,column=c)
        for i in range(6):
            vars=[tk.StringVar(value="CALL"),tk.StringVar(value="COMPRA"),tk.DoubleVar(value=0),tk.DoubleVar(value=1000),tk.DoubleVar(value=0)]
            ws=[ttk.Combobox(lf,textvariable=vars[0],values=["CALL","PUT"],state="readonly",width=8),
                ttk.Combobox(lf,textvariable=vars[1],values=["COMPRA","VENTA"],state="readonly",width=9)]
            ws += [ttk.Entry(lf,textvariable=vars[j],width=9) for j in range(2,5)]
            for c,w in enumerate(ws): w.grid(row=i+1,column=c,padx=2,pady=2)
            self.widgets.append(vars)
        mf=ttk.LabelFrame(left,text="Métricas"); mf.pack(fill="x",pady=8); self.metrics={}
        for i,n in enumerate(["P&L inicial","Delta","Gamma","Vega","Theta","Rho","Máx P&L","Mín P&L","Break-even","Prob. beneficio","P&L esperado"]):
            ttk.Label(mf,text=n).grid(row=i,column=0,sticky="w"); lab=ttk.Label(mf,text="—"); lab.grid(row=i,column=1,sticky="e"); self.metrics[n]=lab
        nb=ttk.Notebook(right); nb.pack(fill="both",expand=True)
        fr=ttk.Frame(nb); nb.add(fr,text="Payoff")
        self.fig=Figure(figsize=(9,6)); self.ax=self.fig.add_subplot(111); self.canvas=FigureCanvasTkAgg(self.fig,fr); self.canvas.get_tk_widget().pack(fill="both",expand=True)
        tf=ttk.Frame(nb); nb.add(tf,text="Escenarios")
        self.tree=ttk.Treeview(tf,columns=["Spot","P&L","Retorno"],show="headings")
        for c in self.tree["columns"]: self.tree.heading(c,text=c)
        self.tree.pack(fill="both",expand=True)
    def legs(self):
        out=[]
        for t,s,q,k,p in self.widgets:
            try: q=float(q.get()); k=float(k.get()); p=float(p.get())
            except: continue
            if q>0: out.append(Leg(t.get(),s.get(),q,k,p))
        return out
    def load_template(self,name):
        tpl=TEMPLATES[name]
        for i,w in enumerate(self.widgets):
            if i<len(tpl):
                x=tpl[i]; w[0].set(x.option_type); w[1].set(x.side); w[2].set(x.quantity); w[3].set(x.strike); w[4].set(x.premium)
            else: w[0].set("CALL"); w[1].set("COMPRA"); w[2].set(0); w[3].set(self.v["spot"].get()); w[4].set(0)
        self.calculate()
    def calculate(self):
        try:
            S=self.v["spot"].get(); iv=self.v["iv"].get(); r=self.v["r"].get(); q=self.v["q"].get(); days=self.v["days"].get(); mult=self.v["mult"].get()
            legs=self.legs(); prices=np.linspace(S*self.v["min"].get(),S*self.v["max"].get(),self.v["points"].get()); pnl=strategy_payoff(prices,legs,mult)
            g=strategy_greeks(S,days,iv,r,q,legs,mult); initial=sum((-1 if x.side=="COMPRA" else 1)*x.quantity*x.premium*mult for x in legs)
            be=approximate_breakevens(prices,pnl); pm=probability_metrics(S,days,iv,r,q,legs,mult)
            vals={"P&L inicial":initial,"Delta":g["delta"],"Gamma":g["gamma"],"Vega":g["vega"],"Theta":g["theta"],"Rho":g["rho"],"Máx P&L":pnl.max(),"Mín P&L":pnl.min(),"Break-even":", ".join(f"{x:.2f}" for x in be) or "—","Prob. beneficio":pm["prob_profit"],"P&L esperado":pm["expected_pnl"]}
            for n,x in vals.items(): self.metrics[n].config(text=f"{x:.2%}" if n=="Prob. beneficio" else (f"{x:,.4f}" if isinstance(x,(float,int,np.floating)) else str(x)))
            self.ax.clear(); self.ax.plot(prices,pnl); self.ax.axhline(0,linewidth=.8); self.ax.axvline(S,linestyle="--",linewidth=.8); self.ax.set_title("Perfil de P&L al vencimiento"); self.ax.set_xlabel("Subyacente"); self.ax.set_ylabel("P&L"); self.ax.grid(alpha=.25); self.fig.tight_layout(); self.canvas.draw()
            for x in self.tree.get_children(): self.tree.delete(x)
            step=max(1,len(prices)//150)
            for i in range(0,len(prices),step): self.tree.insert("", "end",values=(f"{prices[i]:.2f}",f"{pnl[i]:.2f}",f"{pnl[i]/abs(initial):.2%}" if initial else "—"))
        except Exception as e: messagebox.showerror("Error",str(e))
    def export(self):
        S=self.v["spot"].get(); prices=np.linspace(S*self.v["min"].get(),S*self.v["max"].get(),self.v["points"].get()); pnl=strategy_payoff(prices,self.legs(),self.v["mult"].get())
        path=filedialog.asksaveasfilename(defaultextension=".xlsx",filetypes=[("Excel","*.xlsx"),("CSV","*.csv")])
        if path:
            df=pd.DataFrame({"Spot":prices,"P&L":pnl})
            df.to_csv(path,index=False) if path.lower().endswith(".csv") else df.to_excel(path,index=False)
            messagebox.showinfo("Listo","Escenarios exportados.")
