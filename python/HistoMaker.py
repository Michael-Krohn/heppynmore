from samplesclass import sample
from printcolor import printc
import pickle
import ROOT 
from ROOT import TFile, TTree
import ROOT
from array import array
from BetterConfigParser import BetterConfigParser
import sys

class HistoMaker:
    def __init__(self, path, config, region, optionsList,rescale=1,which_weightF='weightF'):
        self.path = path
        self.config = config
        self.optionsList = optionsList
        self.rescale = rescale
        self.which_weightF=which_weightF
        self.region = region
        self.lumi=0.

    def getScale(self,job,subsample=-1):
        anaTag=self.config.get('Analysis','tag')
        input = TFile.Open(self.path+'/'+job.getpath())
        CountWithPU = input.Get("CountWithPU")
        CountWithPU2011B = input.Get("CountWithPU2011B")
        #print lumi*xsecs[i]/hist.GetBinContent(1)
        if subsample>-1:
            xsec=float(job.xsec[subsample])
            sf=float(job.sf[subsample])
        else:
            xsec=float(job.xsec)
            sf=float(job.sf)
        theScale = 1.
        if anaTag == '7TeV':
            theScale = float(self.lumi)*xsec*sf/(0.46502*CountWithPU.GetBinContent(1)+0.53498*CountWithPU2011B.GetBinContent(1))*self.rescale/float(job.split)
        elif anaTag == '8TeV':
            theScale = float(self.lumi)*xsec*sf/(CountWithPU.GetBinContent(1))*self.rescale/float(job.split)
        return theScale 


    def getHistoFromTree(self,job,subsample=-1):
        if self.lumi == 0: raise Exception("You're trying to plot with no lumi")
         
        hTreeList=[]
        groupList=[]


        plot_path = self.config.get('Directories','plotpath')

        # define treeCut
        if job.type != 'DATA':
            if type(self.region)==str:
                cutcut=self.config.get('Cuts',self.region)
            elif type(self.region)==list:
                #replace vars with other vars in the cutstring (used in DC writer)
                cutcut=self.config.get('Cuts',self.region[0])
                cutcut=cutcut.replace(self.region[1],self.region[2])
                #print cutcut
            if subsample>-1:
                treeCut='%s & %s & EventForTraining == 0'%(cutcut,job.subcuts[subsample])        
            else:
                treeCut='%s & EventForTraining == 0'%(cutcut)
        elif job.type == 'DATA':
            cutcut=self.config.get('Cuts',self.region)
            treeCut='%s'%(cutcut)

        # get and skim the Trees
        output=TFile.Open(plot_path+'/tmp_plotCache_%s_%s.root'%(self.region,job.identifier),'recreate')
        input = TFile.Open(self.path+'/'+job.getpath(),'read')
        Tree = input.Get(job.tree)
        output.cd()
        CuttedTree=Tree.CopyTree(treeCut)
    
        # get all Histos at once
        weightF=self.config.get('Weights',self.which_weightF)
        for options in self.optionsList:
            if subsample>-1:
                name=job.subnames[subsample]
                group=job.group[subsample]
            else:
                name=job.name
                group=job.group
            treeVar=options[0]
            name=options[1]
            nBins=int(options[3])
            xMin=float(options[4])
            xMax=float(options[5])

            if job.type != 'DATA':
                if CuttedTree.GetEntries():
                    output.cd() 
                    CuttedTree.Draw('%s>>%s(%s,%s,%s)' %(treeVar,name,nBins,xMin,xMax), weightF, "goff,e")
                    full=True
                else:
                    full=False
            elif job.type == 'DATA':
                if options[11] == 'blind':
                    output.cd()
                    CuttedTree.Draw('%s>>%s(%s,%s,%s)' %(treeVar,name,nBins,xMin,xMax),treeVar+'<0', "goff,e")
                else:
                    output.cd()
                    CuttedTree.Draw('%s>>%s(%s,%s,%s)' %(treeVar,name,nBins,xMin,xMax),'1', "goff,e")
                full = True
            if full:
                hTree = ROOT.gDirectory.Get(name)
            else:
                output.cd()
                hTree = ROOT.TH1F('%s'%name,'%s'%name,nBins,xMin,xMax)
                hTree.Sumw2()
            if job.type != 'DATA':
                ScaleFactor = self.getScale(job,subsample)
                if ScaleFactor != 0:
                    hTree.Scale(ScaleFactor)
            #print '\t-->import %s\t Integral: %s'%(job.name,hTree.Integral())
            hTree.SetDirectory(0)
            input.Close()
            hTreeList.append(hTree)
            groupList.append(group)
            
        return hTreeList, groupList
        

######################
def orderandadd(histos,typs,setup):
#ORDER AND ADD TOGETHER
    ordnung=[]
    ordnungtyp=[]
    num=[0]*len(setup)
    for i in range(0,len(setup)):
        for j in range(0,len(histos)):
            if typs[j] in setup[i]:
                num[i]+=1
                ordnung.append(histos[j])
                ordnungtyp.append(typs[j])
    del histos
    del typs
    histos=ordnung
    typs=ordnungtyp
    print typs
    for k in range(0,len(num)):
        for m in range(0,num[k]):
            if m > 0:
                #add
                histos[k].Add(histos[k+1],1)
                printc('magenta','','\t--> added %s to %s'%(typs[k],typs[k+1]))
                del histos[k+1]
                del typs[k+1]
    del histos[len(setup):]
    del typs[len(setup):]
    return histos, typs