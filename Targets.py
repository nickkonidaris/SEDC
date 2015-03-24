from Tkinter import *

import parse, re
from astropy.table import Table

import Options

reload(parse)
# First create application class
 
 
class Application(Frame):

    data = [] # Data is generated from table
    table = [] # Table is a Table structure from parse
 
    def __init__(self, master=None):
        Frame.__init__(self, master)
         
        self.pack()
        self.create_widgets()
     
    # Create main GUI window
    def create_widgets(self):
        self.search_var = StringVar()
        self.search_var.trace("w", lambda name, index, mode: self.update_list())
        self.entry = Entry(self, textvariable=self.search_var, width=13)
        self.lbox = Listbox(self, width=90, height=20, font='Courier')
        self.refresh_button = Button(self, text="Refresh", command=self.reload_list)
        self.lbl_outfile = Label(self, text="Outfile: %s  |  Infile: %s" % 
            (Options.targets_outfile, Options.targets_infile))
        self.lbox.bind('<<ListboxSelect>>', self.cb_listbox_select)
         
        self.entry.grid(row=0, column=0, padx=10, pady=3)
        self.lbox.grid(row=1, column=0, padx=10, pady=3)
        self.lbl_outfile.grid(row=2, column=0)
        self.refresh_button.grid(row=3,column=0)
         
        # Function for updating the list/doing the search.
        # It needs to be called here to populate the listbox.
        self.update_list()
     

    def reload_list(self):
        ''' Reload from file in current directory '''

        self.table = parse.parse_file2(Options.targets_infile)
        print self.table
        self.update_list()
         
        
    def cb_listbox_select(self, evt):
        ''' Listbox select handler --
            write target to target file'''
        w = evt.widget
        try:
            index = int(w.curselection()[0])
            value = w.get(index)
            print "%d: %s" % (index, value)
            

        except:
            pass

        pos,comment = value.split("#")
        name,ra,dec,epoch= re.split(" +", pos.lstrip().rstrip())
        
        is_hor = "!@~" in comment
        outvals = Table([[name],[float(ra)],[float(dec)],[float(epoch)],[comment], [is_hor]],
            names=('name','RA','Dec','epoch','comment','is_horizon'))
        
        outvals['RA'].unit = 'hour'
        outvals['Dec'].unit = 'degree'
        outvals['epoch'].unit = 'year'
        
        outvals.write(Options.targets_outfile, format="ascii.ipac")
            
    def update_list(self):
        search_term = self.search_var.get()
     
        # Just a generic list to populate the listbox
        self.lbox.delete(0, END)
     
        self.data = []
        for i in xrange(len(self.table)):
            t = self.table[i]
            
            if t['is_horizon']:
                self.data.append("%18s %9.6f %+10.6f %s %s" % 
                    (t['name'], t['ra'], t['dec'], t['epoch'], " ".join(t['comment'])))
            else:
                self.data.append("%18s %9.6f %+10.6f %s %s" % 
                    (t['name'], t['ra'], t['dec'], t['epoch'], " ".join(t['comment'])))

        for i in xrange(len(self.data)):
            item = self.data[i]
            if search_term.lower() in item.lower():
                self.lbox.insert(i, item)
 
 
if __name__ == '__main__':
    root = Tk()
    root.geometry("850x400")
    root.title('SED Machine Next Target')
    app = Application(master=root)
    app.reload_list()
    print 'Starting mainloop()'
    app.mainloop()

