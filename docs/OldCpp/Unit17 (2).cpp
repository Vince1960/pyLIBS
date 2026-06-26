//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include <vcl.h>
#include <string.h>
#include <sys\stat.h>
#include <stdio.h>
#include <fcntl.h>
#include <io.h>
#include <alloc.h>
#include <stdlib.h>
#include <condefs.h>
#include <iostream.h>
#include <fstream.h>
#include <conio.h>
#include <math.h>
#include <sysdefs.h>
#include <dstring.h>
#include <Clipbrd.hpp>
#include <vector.h>
#include "SDIMain.h"
#include "Unit17.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm17 *Form17;
//---------------------------------------------------------------------------
__fastcall TForm17::TForm17(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm17::Button1Click(TObject *Sender)
{
void fit(float x[], float y[], int ndata, float sig[], int mwt, float *a, float *b, float *siga, float *sigb, float *chi2, float *q);
float *vector(long nl,long nh);
float *x,*y,*sig,a,b,siga,sigb,chi2,q;
x=vector(0,5);
y=vector(0,5);
sig=vector(0,5);
x[0]=atof(Form17->Edit1->Text.c_str());
x[1]=atof(Form17->Edit2->Text.c_str());
x[2]=atof(Form17->Edit3->Text.c_str());
x[3]=atof(Form17->Edit4->Text.c_str());
x[4]=atof(Form17->Edit5->Text.c_str());
x[5]=atof(Form17->Edit6->Text.c_str());
y[0]=atof(Form17->Edit7->Text.c_str());
y[1]=atof(Form17->Edit8->Text.c_str());
y[2]=atof(Form17->Edit9->Text.c_str());
y[3]=atof(Form17->Edit10->Text.c_str());
y[4]=atof(Form17->Edit11->Text.c_str());
y[5]=atof(Form17->Edit12->Text.c_str());
sig[0]=atof(Form17->Edit13->Text.c_str());
sig[1]=atof(Form17->Edit14->Text.c_str());
sig[2]=atof(Form17->Edit15->Text.c_str());
sig[3]=atof(Form17->Edit16->Text.c_str());
sig[4]=atof(Form17->Edit17->Text.c_str());
sig[5]=atof(Form17->Edit18->Text.c_str());

Form17->Series1->Clear();
for (int i=0;i<6;i++) Form17->Series1->AddXY(x[i],y[i],' ',clRed);
Form17->Series1->Active=true;
int ndata=6;
int mwt=1;
int i;

fit(x, y, ndata-1, sig, mwt, &a, &b, &siga, &sigb, &chi2, &q);

Form17->Edit19->Text=FormatFloat("#00.00000",a);
Form17->Edit20->Text=FormatFloat("#00.00000",siga);
Form17->Edit21->Text=FormatFloat("#00.00000",b);
Form17->Edit22->Text=FormatFloat("#00.00000",sigb);
Form17->Edit23->Text=FormatFloat("#00.00000",chi2);
Form17->Series2->Clear();
float y1=a+x[0]*b;
float y5=a+x[5]*b;
Form17->Series2->AddXY(x[0],y1,' ',clYellow);
Form17->Series2->AddXY(x[5],y5,' ',clYellow);
Form17->Series2->Active=True;
}
//---------------------------------------------------------------------------


void __fastcall TForm17::Button2Click(TObject *Sender)
{
float *vector(long nl,long nh);
int *ivector(long nl, long nh);
int na;
float *x,*y,*dyda,*sig,*a;
int *ia;
void mrqmin(float x[], float y[], float sig[], int ndata, float a[], int ia[],
int ma, float **covar, float **alpha, float *chisq,
void (*funcs)(float, float [], float *, float [], int), float *alamda);
 void linear(float x, float a[], float *y, float dyda[], int na);
x=vector(0,5);
y=vector(0,5);
sig=vector(0,5);
x[0]=atof(Form17->Edit1->Text.c_str());
x[1]=atof(Form17->Edit2->Text.c_str());
x[2]=atof(Form17->Edit3->Text.c_str());
x[3]=atof(Form17->Edit4->Text.c_str());
x[4]=atof(Form17->Edit5->Text.c_str());
x[5]=atof(Form17->Edit6->Text.c_str());
y[0]=atof(Form17->Edit7->Text.c_str());
y[1]=atof(Form17->Edit8->Text.c_str());
y[2]=atof(Form17->Edit9->Text.c_str());
y[3]=atof(Form17->Edit10->Text.c_str());
y[4]=atof(Form17->Edit11->Text.c_str());
y[5]=atof(Form17->Edit12->Text.c_str());
sig[0]=atof(Form17->Edit13->Text.c_str());
sig[1]=atof(Form17->Edit14->Text.c_str());
sig[2]=atof(Form17->Edit15->Text.c_str());
sig[3]=atof(Form17->Edit16->Text.c_str());
sig[4]=atof(Form17->Edit17->Text.c_str());
sig[5]=atof(Form17->Edit18->Text.c_str());
a=vector(0,1);
ia=ivector(0,1);
dyda=vector(0,1);
a[0]=0.0;
a[1]=1.0;
ia[0]=1;
ia[1]=1;
float alamda=-1.0;
 na=6;
 int ma=1;
 float yy;
 float **matrix(long nrl, long nrh, long ncl, long nch);
            float **covar,**alpha;
           alpha=matrix(0,ma,0,ma);
        covar=matrix(0,ma,0,ma);
       float chisq;
for (int j=0;j<10;j++)
{
mrqmin(x,y,sig,na,a,ia,ma,covar,alpha,&chisq,linear,&alamda);
Form17->Series3->Clear();
float y1=a[0]+x[0]*a[1];
float y5=a[0]+x[5]*a[1];
Form17->Series3->AddXY(x[0],y1,' ',clBlue);
Form17->Series3->AddXY(x[5],y5,' ',clBlue);
Form17->Series3->Active=True;
}
alamda=0.0;
mrqmin(x,y,sig,na,a,ia,ma,covar,alpha,&chisq,linear,&alamda);
 Form17->Edit24->Text=FormatFloat("#00.00",a[0]);
  Form17->Edit25->Text=FormatFloat("#00.00",covar[0][0]);
Form17->Edit26->Text=FormatFloat("#00.00",a[1]);
  Form17->Edit27->Text=FormatFloat("#00.00",covar[1][1]);
Form17->Edit28->Text=FormatFloat("#00.00",chisq);
  Form17->Edit29->Text=FormatFloat("#00.00",covar[0][1]);
  Form17->Edit30->Text=FormatFloat("#00.00",covar[1][0]);

}
//---------------------------------------------------------------------------
 void linear(float x, float a[], float *y, float dyda[], int na)
{
int i;
float fac,ex,arg;
*y=a[0]+a[1]*x;
dyda[0]=1.0;
dyda[1]=x;
}

