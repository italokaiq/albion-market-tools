"""Componentes visuais do aplicativo desktop."""
from tkinter import ttk


def disclosure(parent,title):
    shell=ttk.Frame(parent)
    shell.pack(fill='x',pady=5)
    body=ttk.Frame(shell,padding=(8,6))
    button=ttk.Button(shell,text='+ '+title,style='Quiet.TButton')
    button.pack(anchor='w')
    def toggle():
        if body.winfo_manager():
            body.pack_forget();button.configure(text='+ '+title)
        else:
            body.pack(fill='x');button.configure(text='− '+title)
    button.configure(command=toggle)
    return body


def result_table(parent):
    table=ttk.Treeview(parent,columns=('label','premium','standard'),show='headings',height=7)
    for key,title,width in [('label','Resultado em prata',300),('premium','Premium',200),('standard','Sem Premium',200)]:
        table.heading(key,text=title)
        table.column(key,width=width,anchor='w' if key=='label' else 'e',stretch=True)
    table.tag_configure('profit',foreground='#91D4B9',background='#1C3430')
    table.tag_configure('loss',foreground='#F0AAAA',background='#3B2429')
    table.tag_configure('mixed',foreground='#E5CB91',background='#363026')
    table.pack(fill='x',pady=10)
    return table


def fill_results(table,rows):
    for index,(label,premium,standard) in enumerate(rows):
        values=(label,premium,standard)
        key=str(index)
        tags=()
        if index==0:
            negative=[str(v).startswith('-') for v in (premium,standard)]
            tags=('loss' if all(negative) else 'mixed' if any(negative) else 'profit',)
        if table.exists(key):table.item(key,values=values,tags=tags)
        else:table.insert('', 'end',iid=key,values=values,tags=tags)
    for key in table.get_children():
        if int(key)>=len(rows):table.delete(key)
    table.configure(height=len(rows))
