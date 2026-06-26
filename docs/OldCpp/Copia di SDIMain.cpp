//---------------------------------------------------------------------
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
#include "About.h"
#include "Unit1.h"
#include "Unit2.h"
#include "Unit3.h"
#include "Unit4.h"
#include "Unit5.h"
#include "Unit6.h"
#include "Unit7.h"
#include "Unit9.h"
#include "Unit10.h"
#include "Unit11.h"
#include "Unit12.h"
#include "Unit13.h"
#include "Unit14.h"
#include "Unit16.h"
#include "Unit17.h"
#include "Unit18.h"
#include "Unit19.h"
#include "Unit20.h"
#include "Unit23.h"
#include "Unit25.h"
#include "Unit27.h"
#define COLORE 12632150
#define NR_END 1
#define FREE_ARG char*
static float minarg1,minarg2,jmin,jmax;
static double glaa,glww,glstar,glwlor,gltstar;
#define FMIN(a,b) (minarg1=(a),minarg2=(b),(minarg1) < (minarg2) ? (minarg1) : (minarg2))
#define TINY 1.0e-20
//---------------------------------------------------------------------
#pragma resource "*.dfm"
TSDIAppForm *SDIAppForm;
//---------------------------------------------------------------------
__fastcall TSDIAppForm::TSDIAppForm(TComponent *AOwner)
	: TForm(AOwner)
{
}
//---------------------------------------------------------------------


void __fastcall TSDIAppForm::FileOpen1Execute(TObject *Sender)
{

Chart1->Visible=true;

  OpenDialog->FileName = "";
  Series1->Clear();
  Series2->Clear();
   Series3->Clear();
    Series4->Clear();
  Series5->Clear();
 Chart1->BottomAxis->Automatic=true;
  Chart1->LeftAxis->Automatic=true;

  int handle;
  if (OpenDialog->Execute())
  {
  SaveDialog->FileName = OpenDialog->FileName;

   double   wave;
   double  lips;
   float yyy;
   FILE *stream;
  SDIAppForm->Caption = "Opening File:" + OpenDialog->FileName;
  handle = open((OpenDialog->FileName).c_str(),O_RDONLY);
  stream = fdopen(handle, "r");
   Series1->XValues->Order = loAscending;
  do
   {
   fscanf(stream,"%le %le", &wave, &lips);

    if ((OKBottomDlg->CheckBox7->Checked==true) & (wave < 1500))
    wave=wave*10;

 if ((OKBottomDlg->CheckBox2->Checked==true) & (OKBottomDlg->RadioButton1->Checked==true))
 {
  for (int k=1; k < Form10->Series1->Count(); k++)
{
 if (wave < Form10->Series1->XValues->Value[k])
{
yyy=Form10->Series1->YValues->Value[k]+
(Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
(Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
(wave-Form10->Series1->XValues->Value[k]);
 lips/=yyy;
 goto apa;
 }
}
}
apa:

  if ((wave <= atof(OKBottomDlg->Edit4->Text.c_str())) & (wave >= atof(OKBottomDlg->Edit3->Text.c_str())))
   Series1->AddXY(wave,lips,' ',clBlack);
    }
  while (!eof(handle));
   close(handle);
     AnsiString fn=ExtractFilePath(Application->ExeName)+"\Templates\\template.db";
   Form6->Table1->Active = false;
    Form6->Table1->TableName=fn;
    Form6->Table1->EmptyTable();
    SDIAppForm->Series4->Clear();
    Form6->Table1->Active = true;
   SDIAppForm->Caption = "Current File:" + OpenDialog->FileName;
  }
}

//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::FileSave1Execute(TObject *Sender)
{
	TVarRec vrs[1];
          char stringa[80]="The file already exists. Overwrite?";
	if (SaveDialog->Execute())
	{
		if (FileExists(SaveDialog->FileName))
		{
			if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
				mbCancel, 0) != IDYES)
				return;
		}

  FILE *out;

   out = fopen((SaveDialog->FileName).c_str(), "w");

        int w;
      for (w=Series1->FirstValueIndex;w<Series1->LastValueIndex+1;w++)
      {
       fprintf(out,"%f %f\n", Series1->XValues->Value[w], Series1->YValues->Value[w]);
      }
         fclose(out);
	}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::FileExit1Execute(TObject *Sender)
{
  Close();
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::HelpAbout1Execute(TObject *Sender)
{
  AboutBox->ShowModal();        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Import1Click(TObject *Sender)
{
int handle;
OpenDialog->FileName = "";
   OpenDialog->Filter = "ASCII Files (*.dat)|*.DAT|All Files (*.*)|*.*";
   OpenDialog->Options << ofAllowMultiSelect;
  if (OpenDialog->Execute())
  {
     OKBottomDlg->RadioButton1->Checked=false;
 OKBottomDlg->RadioButton2->Checked=true;
  SaveDialog->FileName = OpenDialog->FileName;
  Memo1->Lines=OpenDialog->Files;
    if (OKBottomDlg->CheckBox1->Checked==true)
{
float xf,yf;

Form12->Series1->Clear();

   FILE *strm;
  strm = fopen(OKBottomDlg->Edit11->Text.c_str(), "rt");
   int idx=0;
 do
   {
   idx++;
   fscanf(strm,"%g %g", &xf, &yf);

   Form12->Series1->AddXY(idx,yf,' ',clBlack);
    }

while(!feof(strm));
   fclose(strm);
   }

   int j;
   double  wave;
   double  lips;
        FILE *stream;
   int handle;
   for (j=0;j<Memo1->Lines->Count;j++)
   {
  SDIAppForm->Caption = "Importing File:" + Memo1->Lines->Strings[j];
  handle=open((Memo1->Lines->Strings[j]).c_str(),O_RDONLY);
  stream = fdopen(handle, "r");
  int ndata=0;
   Series1->XValues->Order = loAscending;
 do
   {
 ndata++;
 fscanf(stream,"%le %le", &wave, &lips);

    if (OKBottomDlg->CheckBox1->Checked==true)
    {
      float norma=Form12->Series1->YValues->Value[ndata];
       lips/=norma;
    }

  if ((OKBottomDlg->CheckBox7->Checked==true) & (wave < 1500))
    wave=wave*10;

    Series1->AddXY(wave+atof(OKBottomDlg->Edit23->Text.c_str()),lips,' ',clBlack);
   }
   while (!eof(handle));
   close(handle);

      SDIAppForm->Caption = "Current File:" + OpenDialog->FileName;
  }
}
}
//---------------------------------------------------------------------------



 
void __fastcall TSDIAppForm::Convert1Click(TObject *Sender)
{
int handle;
  OpenDialog->FileName = "";
     OpenDialog->Options << ofAllowMultiSelect;
   OpenDialog->Filter = "PRISM Files (*.l00)|*.L00|All Files (*.*)|*.*";
  if (OpenDialog->Execute())
  {
   OKBottomDlg->RadioButton1->Checked=false;
 OKBottomDlg->RadioButton2->Checked=true;
  SaveDialog->FileName = OpenDialog->FileName;
  Memo1->Lines=OpenDialog->Files;

   if (OKBottomDlg->CheckBox1->Checked==true)
{

float xf,yf;

Form12->Series1->Clear();

   FILE *strm;
  strm = fopen(OKBottomDlg->Edit11->Text.c_str(), "rt");
   int idx=0;

 do
   {
   idx++;
   fscanf(strm,"%g %g", &xf, &yf);

   Form12->Series1->AddXY(idx,yf,' ',clBlack);
    }

while(!feof(strm));
   fclose(strm);
   }

      int w;
   int handle;
     void *heade;
   double dt[8];
   double x;
    double y;
      char buff;
       int j;

   for (j=0;j<Memo1->Lines->Count;j++)
   {
  SDIAppForm->Caption = "Converting File:" + Memo1->Lines->Strings[j];
  handle=open((Memo1->Lines->Strings[j]).c_str(),O_RDONLY|O_BINARY);
      heade=malloc(1539);
    read(handle, heade, 1539);
            read(handle,&dt,64);
          heade=malloc(64);
             read(handle, heade, 64);
          int fin=0;
       int flag=0;
         int nn=0;
        int ndata=0;
   do
   {
      if (nn < 48)
      {
      fin=48;
      }
      else
      {
      fin=64;
      }
   for (w=0;w<fin;w++)
   {
     read(handle,&y,8);
      ndata++;
    if (OKBottomDlg->CheckBox1->Checked==true)
    {
      float norma=Form12->Series1->YValues->Value[ndata];
       y/=norma;
    }

       x=dt[0]+nn*dt[1];
             Series1->AddXY(x+atof(OKBottomDlg->Edit23->Text.c_str()),y,' ',clBlack);
      nn++;
      if (nn==(dt[2]-1))
      {
      flag=1;
      w=fin;
      }
      }
     if (flag==0)
     {
      read(handle,&buff,1);
     }
    }
    while (flag!=1);
   close(handle);
      SDIAppForm->Caption = "Current File:" + OpenDialog->FileName;
   }
    }
 }

//---------------------------------------------------------------------------



 void spline(float x[],float y[],int n, float y2[])
 {
 int i,k;
 float p,qn,sig,un,*u;
 float *vector(long nl,long nh);
 u=vector(0,n-1);
 y2[0]=u[0]=0.0;
  for (i=1;i<n-1;i++);
   sig=(x[i]-x[i-1])/(x[i+1]-x[i-1]);
    p=sig*y2[i-1]+2.0;
     y2[i]=(sig-1.0)/p;
    u[i]=(y[i+1]-y[i])/(x[i+1]-x[i])-(y[i]-y[i-1])/(x[i]-x[i-1]);
    u[i]=(6.0*u[i]/(x[i+1]-x[i-1])-sig*u[i-1])/p;
    qn=un=0.0;
     y2[n]=(un-qn*u[n-1])/(qn*y2[n-1]+1.0);
     for (k=n-1;k>=0;k--)
     y2[k]=y2[k]*y2[k+1]+u[k];
 }
 //--------------------------------------------------------------------------

 void splint(float xa[],float ya[],float y2a[],int n, float x, float *y)
 {
 int klo,khi,k;
 float h,b,a;
 klo=0;
 khi=n;
 while (khi-klo >1)
 {
 k=(khi+klo) >>1;
  if (xa[k] >x) khi=k;
  else klo=k;
  }
  h=xa[khi]-xa[klo];
  a=(xa[khi]-x)/h;
  b=(x-xa[klo])/h;
  *y=a*ya[klo]+b*ya[khi]+((a*a*a-a)*y2a[klo]+(b*b*b-b)*y2a[khi])*(h*h)/6.0;
   }
//--------------------------------------------------------------------------

float *vector(long nl,long nh)
{
 float *v;
 v=(float *)malloc((size_t) ((nh-nl+1+NR_END)*sizeof(float)));
 return v-nl+NR_END;
}
//--------------------------------------------------------------------------




int *ivector(long nl, long nh)
/* allocate an int vector with subscript range v[nl..nh] */
{
int *v;
v=(int *)malloc((size_t) ((nh-nl+1+NR_END)*sizeof(int)));
return v-nl+NR_END;
}
//---------------------------------------------------------------------------

float **matrix(long nrl, long nrh, long ncl, long nch)
/* allocate a float matrix with subscript range m[nrl..nrh][ncl..nch] */
{
long i, nrow=nrh-nrl+1,ncol=nch-ncl+1;
float **m;
/* allocate pointers to rows */
m=(float **) malloc((size_t)((nrow+NR_END)*sizeof(float*)));
m += NR_END;
m -= nrl;
/* allocate rows and set pointers to them */
m[nrl]=(float *) malloc((size_t)((nrow*ncol+NR_END)*sizeof(float)));
m[nrl] += NR_END;
m[nrl] -= ncl;
for(i=nrl+1;i<=nrh;i++) m[i]=m[i-1]+ncol;
/* return pointer to array of pointers to rows */
return m;
}
//---------------------------------------------------------------------------

void ludcmp(float **a, int n, int *indx, float *d)
{
float *vector(long nl,long nh);

int i,imax,j,k;
float big,dum,sum,temp;
float *vv;
vv=vector(1,n);
*d=1.0;
for (i=1;i<=n;i++)
{
big=0.0;
for (j=1;j<=n;j++)
if ((temp=fabs(a[i][j])) > big) big=temp;
vv[i]=1.0/big;
}
for (j=1;j<=n;j++)
{
for (i=1;i<j;i++)
{
sum=a[i][j];
for (k=1;k<i;k++) sum -= a[i][k]*a[k][j];
a[i][j]=sum;
}
big=0.0;
for (i=j;i<=n;i++)
{
sum=a[i][j];
for (k=1;k<j;k++)
sum -= a[i][k]*a[k][j];
a[i][j]=sum;
if ( (dum=vv[i]*fabs(sum)) >= big) {
big=dum;
imax=i;
}
}
if (j != imax)
{
for (k=1;k<=n;k++)
{
dum=a[imax][k];
a[imax][k]=a[j][k];
a[j][k]=dum;
}
*d = -(*d);
vv[imax]=vv[j];
}
indx[j]=imax;
if (a[j][j] == 0.0) a[j][j]=TINY;
if (j != n)
{
dum=1.0/(a[j][j]);
for (i=j+1;i<=n;i++) a[i][j] *= dum;
}
}
}
//---------------------------------------------------------------------------

void lubksb(float **a, int n, int *indx, float b[])
{
int i,ii=0,ip,j;
float sum;
for (i=1;i<=n;i++)
{
ip=indx[i];
sum=b[ip];
b[ip]=b[i];
if (ii)
for (j=ii;j<=i-1;j++) sum -= a[i][j]*b[j];
else if (sum) ii=i;
b[i]=sum;
}
for (i=n;i>=1;i--)
{
sum=b[i];
for (j=i+1;j<=n;j++) sum -= a[i][j]*b[j];
b[i]=sum/a[i][i];
}
}
//---------------------------------------------------------------------------

void savgol(float c[], int np, int nl, int nr, int ld, int m)
{
void lubksb(float **a, int n, int *indx, float b[]);
void ludcmp(float **a, int n, int *indx, float *d);
int *ivector(long nl, long nh);
float **matrix(long nrl, long nrh, long ncl, long nch);
float *vector(long nl,long nh);
void ludcmp(float **a, int n, int *indx, float *d);

int imj,ipj,j,k,kk,mm,*indx;
float d,fac,sum,**a,*b;

       indx=ivector(1,m+1);
       a=matrix(1,m+1,1,m+1);
       b=vector(1,m+1);


for (ipj=0;ipj<=(m << 1);ipj++)
{
sum=(ipj ? 0.0 : 1.0);
for (k=1;k<=nr;k++) sum += pow((double)k,(double)ipj);
for (k=1;k<=nl;k++) sum += pow((double)-k,(double)ipj);
mm=FMIN(ipj,2*m-ipj);
for (imj = -mm;imj<=mm;imj+=2) a[1+(ipj+imj)/2][1+(ipj-imj)/2]=sum;
}
ludcmp(a,m+1,indx,&d);
for (j=1;j<=m+1;j++) b[j]=0.0;
b[ld+1]=1.0;

lubksb(a,m+1,indx,b);
for (kk=1;kk<=np;kk++) c[kk]=0.0;
for (k = -nl;k<=nr;k++)
{
sum=b[1];
fac=1.0;
for (mm=1;mm<=m;mm++) sum += b[mm+1]*(fac *= k);
c[nl+k+1]=sum;
}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Button5Click(TObject *Sender)
{
void savgol(float c[], int np, int nl, int nr, int ld, int m);
float *vector(long nl,long nh);
float *a;
int *ia;
void mrqmin(float x[], float y[], float sig[], int ndata, float a[], int ia[],
int ma, float **covar, float **alpha, float *chisq,
void (*funcs)(float, float [], float *, float [], int), float *alamda);
void fgauss(float x, float a[], float *y, float dyda[], int na);
int sign(float a);

     TMsgDlgButtons msbut;
        msbut.Clear();
         msbut << mbYes << mbNo << mbCancel;
    int ss=MessageDlg("This operation will clear the current template. The operation is not undoable. Continue?",mtConfirmation,msbut,0);
          switch (ss)
          {
          case mrYes:
          break;
          case mrNo:
          case mrCancel:
          return;
          }

AnsiString fn=ExtractFilePath(Application->ExeName)+"\Templates\\template.db";
Edit8->Text=fn;
 Form6->Table1->Active = false;
//  Form6->Query1->Active = false;
 Form6->Table1->TableName=fn;
 Form6->Table1->EmptyTable();
 SDIAppForm->Series4->Clear();
 Form6->Table1->Active = true;
// Form6->Query1->Active = true;
      Form6->Show();

  int m,nl,nr,ld,np,z;
   float *c;
       m= atof((OKBottomDlg->Edit6->Text).c_str());
     nl= atof((OKBottomDlg->Edit5->Text).c_str());
      nr=atof((OKBottomDlg->Edit5->Text).c_str());
       ld=2;
         np=nl+nr+1;
              c=vector(1,np);

   savgol(c, np, nl, nr, ld, m);

       int k;

    Series2->Clear();
     Series3->Clear();

    float xx,y;

   for (k=nl;k<Series1->Count()-nr;k++)
    {xx=Series1->XValues->Value[k];
    y=0;
     for (z=-nl;z<nr+1;z++)
     {
     y+=(c[nl+z+1])*Series1->YValues->Value[k+z];
    }
    Series2->AddXY(xx,y,' ',clBlack);
    }
       Chart1->LeftAxis->Automatic=true;
    Series1->Active=false;
    Series2->Active=true;

 float minhist,maxhist,dx;
   float ndata=100;

  minhist=Series2->MinYValue();
    maxhist=Series2->MaxYValue();
     dx=(maxhist-minhist)/ndata;

float histo[1000]={0.0};
  float x[1000];

     int pos;
        float sig[1000];

     for (z=0;z<Series2->Count()-1;z++)
     {
      pos=(Series2->YValues->Value[z]-minhist)/dx;
      if (pos<ndata) histo[pos]++;
     }
         Series3->Clear();

    for (z=0;z<ndata;z++)
    {
    x[z]=z*dx+minhist;
      sig[z]=100;
    Series3->AddXY(x[z],histo[z],' ',clBlack);
    }
         Series1->Active=false;
         Series2->Active=false;
          Series3->Active=true;

          int ma=2;
          a=vector(0,ma);
           ia=ivector(0,ma);
        a[0]=Series3->MaxYValue();
        a[1]=0;
        a[2]=Series3->MaxXValue()/10;
         ia[0]=1;
         ia[1]=0;
         ia[2]=1;
           float **covar,**alpha;
           alpha=matrix(0,ma,0,ma);
        covar=matrix(0,ma,0,ma);
            float chisq;

             float alamda;
             alamda=-1.0;
             int u;

        for (u=1;u<50;u++)
          {
          mrqmin(x,histo,sig,ndata,a,ia,ma,covar,alpha,&chisq,fgauss,&alamda);
          if (atof(SDIAppForm->Edit3->Text.c_str()) != 0)
          break;
          }

     Series2->Active=true;
     Series3->Active=false;
     Series1->Active=false;

     Series4->Clear();

    int g;
    char wavel[80];
     float shift;
      float threshold;
       threshold=atof((OKBottomDlg->Edit7->Text).c_str());
    for (g=1;g<Series2->Count()-2;g++)
    {
    if ((sign(Series2->YValues->Value[g-1]-Series2->YValues->Value[g]) != sign(Series2->YValues->Value[g]-Series2->YValues->Value[g+1])) && (Series2->YValues->Value[g] <0))
    {
     if (fabs(Series2->YValues->Value[g]) > a[2]*threshold)
     {
     sprintf(wavel,"%4.2f", Series2->XValues->Value[g]);
     shift=atof((OKBottomDlg->Edit5->Text).c_str());
     Series4->AddXY(Series2->XValues->Value[g],Series1->YValues->Value[g+shift],wavel,clBlue);
     Form6->Table1->Edit();
     Form6->Table1->FieldValues["wavelen"]=Series2->XValues->Value[g];
     Form6->Table1->FieldValues["asswavelen"]=Series2->XValues->Value[g];
     Form6->Table1->FieldValues["templint"]=Series1->YValues->Value[g+shift];
     Form6->Table1->Append();
     }
    }
    }
    Series2->Active=false;
    Series3->Active=false;
    Series1->Active=true;
    Series4->Active=true;
        Form6->Table1->Refresh();
        Form6->Table1->First();
}
//---------------------------------------------------------------------------

void mrqmin(float x[], float y[], float sig[], int ndata, float a[], int ia[],
int ma, float **covar, float **alpha, float *chisq,
void (*funcs)(float, float [], float *, float [], int), float *alamda)
{
void covsrt(float **covar, int ma, int ia[], int mfit);
void gaussj(float **a, int n, float **b, int m);
void mrqcof(float x[], float y[], float sig[], int ndata, float a[],
int ia[], int ma, float **alpha, float beta[], float *chisq,
void (*funcs)(float, float [], float *, float [], int));
float *vector(long nl,long nh);
void free_matrix(float **m, long nrl, long nrh, long ncl, long nch);
void free_vector(float *v, long nl, long nh);
int j,k,l;
static int mfit;
static float ochisq,*atry,*beta,*da,**oneda;
if (*alamda < 0.0)
{
atry=vector(0,ma);
beta=vector(0,ma);
da=vector(0,ma);

for (mfit=-1,j=0;j<=ma;j++)
if (ia[j]) mfit++;
oneda=matrix(0,mfit,0,0);
*alamda=0.001;
mrqcof(x,y,sig,ndata,a,ia,ma,alpha,beta,chisq,funcs);
ochisq=(*chisq);

for (j=0;j<=ma;j++) atry[j]=a[j];
}
for (j=0;j<=mfit;j++) {
for (k=0;k<=mfit;k++) covar[j][k]=alpha[j][k];
covar[j][j]=alpha[j][j]*(1.0+(*alamda));
oneda[j][0]=beta[j];
}

gaussj(covar,mfit,oneda,0);
for (j=0;j<=mfit;j++) da[j]=oneda[j][0];
if (*alamda == 0.0)
{
covsrt(covar,ma,ia,mfit);
return;
}
for (j=-1,l=0;l<=ma;l++)
if (ia[l]) atry[l]=a[l]+da[++j];
mrqcof(x,y,sig,ndata,atry,ia,ma,covar,da,chisq,funcs);
if (*chisq < ochisq)
{
*alamda *= 0.1;
ochisq=(*chisq);
for (j=0;j<=mfit;j++)
{
for (k=0;k<=mfit;k++) alpha[j][k]=covar[j][k];
beta[j]=da[j];
}
for (l=0;l<=ma;l++) a[l]=atry[l];
}
else
{
*alamda *= 10.0;
*chisq=ochisq;
}
}
//---------------------------------------------------------------------------

void mrqcof(float x[], float y[], float sig[], int ndata, float a[], int ia[],
int ma, float **alpha, float beta[], float *chisq,
void (*funcs)(float, float [], float *, float [], int))
{
void free_vector(float *v, long nl, long nh);
float *vector(long nl,long nh);
int i,j,k,l,m,mfit=0;
float ymod,wt,sig2i,dy,*dyda;

dyda=vector(0,ma);
for (j=0;j<ma;j++)
if (ia[j]) mfit++;
for (j=0;j<=mfit;j++)
{
for (k=0;k<=j;k++)
{
alpha[j][k]=0.0;
}
beta[j]=0.0;
}
*chisq=0.0;
for (i=0;i<=ndata-1;i++) {
(*funcs)(x[i],a,&ymod,dyda,ma);
sig2i=1.0/(sig[i]*sig[i]);
dy=y[i]-ymod;
for (j=-1,l=0;l<=ma;l++) {
if (ia[l]) {
wt=dyda[l]*sig2i;
for (j++,k=-1,m=0;m<=l;m++)
{
if (ia[m]) alpha[j][++k] += wt*dyda[m];
}
beta[j] += dy*wt;
}
}
*chisq += dy*dy*sig2i;
}

 for (j=1;j<=mfit;j++)
for (k=0;k<j;k++) alpha[k][j]=alpha[j][k];
free_vector(dyda,0,ma);
}
//---------------------------------------------------------------------------

void fgauss(float x, float a[], float *y, float dyda[], int na)
{
float arg,ex,fac;
arg=(x-a[1])/a[2];
ex=exp(-arg*arg);
fac=a[0]*ex*2.0*arg;
*y=a[0]*ex;
dyda[0]=ex;
dyda[1]=fac/a[2];
dyda[2]=fac*arg/a[2];
}
//---------------------------------------------------------------------------
 void autogauss(float x, float a[], float *y, float dyda[], int na)
{
    int i,j,npeaks;

npeaks=(na-1)/3.0;

   for (j=1;j<na;j++)
   {
    a[j]=fabs(a[j]);
   }

  *y=a[0]+a[na]*x;

 dyda[0]=1.0;
  dyda[na]=x;

  for (j=1;j<na;j++)
 {
 dyda[j]=0;
 }

 for (j=0;j<npeaks;j++)
 {
 float arg,ex,fac;
arg=(x-a[2+3*j])/a[3+3*j];
ex=exp(-arg*arg);
fac=a[1+3*j]*ex*2.0*arg;
*y+=a[1+3*j]*ex;
dyda[1+3*j]+=ex;
dyda[2+3*j]+=fac/a[3+3*j];
dyda[3+3*j]+=fac*arg/a[3+3*j];
  }
 }

//---------------------------------------------------------------------------
void covsrt(float **covar, int ma, int ia[], int mfit)

{
int i,j,k;
for (i=mfit+1;i<=ma;i++)
for (j=0;j<=i;j++) covar[i][j]=covar[j][i]=0.0;
k=mfit;
for (j=ma;j>=0;j--) {
if (ia[j]) {
for (i=0;i<=ma;i++) swap(covar[i][k],covar[i][j]);
for (i=0;i<=ma;i++) swap(covar[k][i],covar[j][i]);
k--;
}
}
}
//---------------------------------------------------------------------------

void free_vector(float *v, long nl, long nh)
/* free a float vector allocated with vector() */
{
free((FREE_ARG) (v+nl-NR_END));
}
void free_ivector(int *v, long nl, long nh)
/* free an int vector allocated with ivector() */
{
free((FREE_ARG) (v+nl-NR_END));
}
void free_cvector(unsigned char *v, long nl, long nh)
/* free an unsigned char vector allocated with cvector() */
{
free((FREE_ARG) (v+nl-NR_END));
}
void free_lvector(unsigned long *v, long nl, long nh)
/* free an unsigned long vector allocated with lvector() */
{
free((FREE_ARG) (v+nl-NR_END));
}
void free_dvector(double *v, long nl, long nh)
/* free a double vector allocated with dvector() */
{
free((FREE_ARG) (v+nl-NR_END));
}
void free_matrix(float **m, long nrl, long nrh, long ncl, long nch)
/* free a float matrix allocated by matrix() */
{
free((FREE_ARG) (m[nrl]+ncl-NR_END));
free((FREE_ARG) (m+nrl-NR_END));
}
void free_dmatrix(double **m, long nrl, long nrh, long ncl, long nch)
/* free a double matrix allocated by dmatrix() */
{
free((FREE_ARG) (m[nrl]+ncl-NR_END));
free((FREE_ARG) (m+nrl-NR_END));
}
void free_imatrix(int **m, long nrl, long nrh, long ncl, long nch)
/* free an int matrix allocated by imatrix() */
{
free((FREE_ARG) (m[nrl]+ncl-NR_END));
free((FREE_ARG) (m+nrl-NR_END));
}
void free_submatrix(float **b, long nrl, long nrh, long ncl, long nch)
/* free a submatrix allocated by submatrix() */
{
free((FREE_ARG) (b+nrl-NR_END));
}
void free_convert_matrix(float **b, long nrl, long nrh, long ncl, long nch)
/* free a matrix allocated by convert_matrix() */
{
free((FREE_ARG) (b+nrl-NR_END));
}
void free_f3tensor(float ***t, long nrl, long nrh, long ncl, long nch,
long ndl, long ndh)
/* free a float f3tensor allocated by f3tensor() */
{
free((FREE_ARG) (t[nrl][ncl]+ndl-NR_END));
free((FREE_ARG) (t[nrl]+ncl-NR_END));
free((FREE_ARG) (t+nrl-NR_END));
}
//---------------------------------------------------------------------------

void gaussj(float **a, int n, float **b, int m)
{
int *indxc,*indxr,*ipiv;
int i,icol,irow,j,k,l,ll;
double big;
float dum,pivinv;
void free_ivector(int *v, long nl, long nh);

indxc=ivector(0,n);
indxr=ivector(0,n);
ipiv=ivector(0,n);
for (j=0;j<=n;j++) ipiv[j]=0;
for (i=0;i<=n;i++)
{
big=0.0;
for (j=0;j<=n;j++)
if (ipiv[j] != 1)
for (k=0;k<=n;k++)
{
if (ipiv[k] == 0)
{
if (fabs(a[j][k]) >= big)
{
big=fabs(a[j][k]);
// SDIAppForm->Edit3->Text=big;
irow=j;
icol=k;
}
}
else if (ipiv[k] > 1) ShowMessage("Singular matrix");
}
++(ipiv[icol]);
if (irow != icol)
{
for (l=0;l<=n;l++) swap(a[irow][l],a[icol][l]);
for (l=0;l<=m;l++) swap(b[irow][l],b[icol][l]);
}
indxr[i]=irow;
indxc[i]=icol;
if (a[icol][icol] == 0) ShowMessage("Singular matrix");
pivinv=1.0/a[icol][icol];
a[icol][icol]=1.0;
for (l=0;l<=n;l++) a[icol][l] *= pivinv;
for (l=0;l<=m;l++) b[icol][l] *= pivinv;
for (ll=0;ll<=n;ll++)
if (ll != icol)
{
dum=a[ll][icol];
a[ll][icol]=0.0;
for (l=0;l<=n;l++) a[ll][l] -= a[icol][l]*dum;
for (l=0;l<=m;l++) b[ll][l] -= b[icol][l]*dum;
}
}
for (l=n;l>=0;l--) {
if (indxr[l] != indxc[l])
for (k=0;k<=n;k++)
swap(a[k][indxr[l]],a[k][indxc[l]]);
}
free_ivector(ipiv,0,n);
free_ivector(indxr,0,n);
free_ivector(indxc,0,n);
}
//---------------------------------------------------------------------------

int sign(float a)
{
   int s;
  if (a==0) s=0;
  if (a>0) s=1;
  if (a<0) s=-1;
return s;
}
//---------------------------------------------------------------------------


void __fastcall TSDIAppForm::Button7Click(TObject *Sender)
{
Form2->Show();
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Chart1MouseMove(TObject *Sender,
      TShiftState Shift, int X, int Y)
{
float fattx,fatty,xx,yy,capx,capy;
if ((Chart1->ChartWidth == 0) || (Chart1->ChartHeight == 0))
{
Label1->Caption="0000.00";
Label2->Caption="0000.00";
}
else
{
xx=X;
yy=Y;
fattx=((xx-Chart1->ChartRect.Left)/(Chart1->ChartWidth));
fatty=((yy-Chart1->ChartRect.Bottom)/(Chart1->ChartHeight));
capx=Chart1->BottomAxis->Minimum+fattx*(Chart1->BottomAxis->Maximum-Chart1->BottomAxis->Minimum);
capy=Chart1->LeftAxis->Minimum-fatty*(Chart1->LeftAxis->Maximum-Chart1->LeftAxis->Minimum);
Label1->Caption=FormatFloat("#0000.00",capx);
Label2->Caption=FormatFloat("#0000.00",capy);
}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Chart1MouseDown(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
void identif(float xx);
if (Button==mbLeft && Shift.Contains(ssAlt) && Shift.Contains(ssCtrl))
 {
 Form4->Show();
 Form4->Edit1->Text=Label2->Caption.c_str();
 return;
 }
 else if (Button==mbRight && Shift.Contains(ssAlt)&& Shift.Contains(ssCtrl))
 {
 Form4->Show();
    Form4->Edit2->Text=Label2->Caption.c_str();
 return;
 }
else if (Button==mbLeft && Shift.Contains(ssShift))
 {
 float xx=atof(Label1->Caption.c_str());
identif(xx);
}

 else if (Button==mbLeft && Shift.Contains(ssCtrl))
 {
Form5->Show();
char sqls[300];
float range,freq;
range=atof(OKBottomDlg->Edit9->Text.c_str());
 freq=atof(Label1->Caption.c_str());
  Form5->Edit1->Text=Label1->Caption.c_str();
sprintf(sqls,"SELECT * FROM daticerti WHERE [wavelen] BETWEEN %f AND %f ORDER BY abs([wavelen]-%f)",(freq-range),(freq+range),freq);
  Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 }
 else if (Button==mbLeft && Shift.Contains(ssAlt))
 {
 Form11->Show();
 Form11->Edit1->Text=Label1->Caption.c_str();
 }
 else if (Button==mbRight && Shift.Contains(ssAlt))
 {
 Form11->Show();
    Form11->Edit2->Text=Label1->Caption.c_str();
 }
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Chart1DblClick(TObject *Sender)
{
Form5->Show();
char sqls[300];
float range,freq;
range=atof(OKBottomDlg->Edit9->Text.c_str());
 freq=atof(Label1->Caption.c_str());
  Form5->Edit1->Text=Label1->Caption.c_str();

sprintf(sqls,"SELECT * FROM datalibs WHERE [wavelen] BETWEEN %f AND %f ORDER BY abs([wavelen]-%f)",(freq-range),(freq+range),freq);
  Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
}
//---------------------------------------------------------------------------


void __fastcall TSDIAppForm::nmA1Click(TObject *Sender)
{
int u;
u=Series1->XValues->Count();
Series2->Clear();
 for (int z=0;z<u;z++)
{
 Series2->AddXY(Series1->XValues->Value[z]*10.,Series1->YValues->Value[z],' ',clBlack);
}
Series1->Active=False;
swap(Series1,Series2);
Series2->Active=False;
Series1->Active=True;
}
//---------------------------------------------------------------------------

void gauss(float x, float a[], float *y, float dyda[], int na)
{
int i;
float fac,ex,arg;
*y=a[0];
dyda[0]=1.0;
for (i=1;i<=na-1;i+=3) {
arg=(x-a[i+1])/a[i+2];
ex=exp(-arg*arg);
fac=a[i]*ex*2.0*arg;
*y += a[i]*ex;
dyda[i]=ex;
dyda[i+1]=fac/a[i+2];
dyda[i+2]=fac*arg/a[i+2];
}
}

//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Button6Click(TObject *Sender)
{
void autofit(float jmin, float jmax, int j);
      float jmin=SDIAppForm->Series4->FirstValueIndex;
      float jmax=SDIAppForm->Series4->LastValueIndex;
      int j=jmin;
      SDIAppForm->Edit10->Text=jmin;
      SDIAppForm->Edit11->Text=jmax;
      SDIAppForm->Edit12->Text=j;
        Form14->ProgressBar1->Position=0;
      Form14->Show();
     autofit(jmin, jmax, j);
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Resample1Click(TObject *Sender)
{
  int npoints;

        if  (OKBottomDlg->Edit3->Text<Series1->XValues->MinValue)
        {
        OKBottomDlg->Edit3->Text=Series1->XValues->MinValue;
        }
        if  (OKBottomDlg->Edit4->Text>Series1->XValues->MaxValue)
        {
        OKBottomDlg->Edit4->Text=Series1->XValues->MaxValue;
         }

      npoints=(atof((OKBottomDlg->Edit4->Text).c_str())-atof((OKBottomDlg->Edit3->Text).c_str()))/atof((OKBottomDlg->Edit2->Text).c_str());

         Series2->Clear();
  int oldj=0;
  float xx,yy;
  xx=atof((OKBottomDlg->Edit3->Text).c_str());
  for (int i=1;i<npoints;i++)
  {
  xx+=atof((OKBottomDlg->Edit2->Text).c_str());
   for (int j=oldj; j < Series1->Count(); j++)
  {
  if (xx < Series1->XValues->Value[j])
  {
  yy=Series1->YValues->Value[j];
  oldj=j;
  break;
  }
  }
  Series2->AddXY(xx,yy,' ',clBlack);
  }
  swap(Series1,Series2);
  Series2->Active=false;
  Series1->Active=true;
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Smooth1Click(TObject *Sender)
{
 void savgol(float c[], int np, int nl, int nr, int ld, int m);
   float *vector(long nl,long nh);

  int m,nl,nr,ld,np;
  float *c;

   m= atof((OKBottomDlg->Edit6->Text).c_str());
     nl= atof((OKBottomDlg->Edit5->Text).c_str());
      nr=atof((OKBottomDlg->Edit5->Text).c_str());
       ld=atof((OKBottomDlg->Edit1->Text).c_str());
         np=nl+nr+1;
              c=vector(1,np);

   savgol(c, np, nl, nr, ld, m);

       int k,z;

    Series2->Clear();
    float x,y;
   for (k=nl;k<Series1->Count()-nr;k++)
    {x=Series1->XValues->Value[k];
    y=0;
     for (z=-nl;z<nr+1;z++)
     {
     y+=(c[nl+z+1])*Series1->YValues->Value[k+z];
    }
    Series2->AddXY(x,y,' ',clBlack);
    }
   swap (Series1,Series2);
   Series1->Active=true;
    Series2->Active=false;        
}
//---------------------------------------------------------------------------






void __fastcall TSDIAppForm::LoadTempl1Click(TObject *Sender)
{
void loadtempl(AnsiString nome);
  SDIAppForm->OpenDialog1->Title="Load Template";
 SDIAppForm->OpenDialog1->Filter = "Templates|*.DB";
 SDIAppForm->OpenDialog1->FileName = "*.DB";
 SDIAppForm->OpenDialog1->InitialDir=ExtractFilePath(Application->ExeName)+"Templates";
  if (SDIAppForm->OpenDialog1->Execute())
  {
 SDIAppForm->Edit8->Text=SDIAppForm->OpenDialog1->FileName;
 loadtempl(SDIAppForm->OpenDialog1->FileName);
 }
}
//---------------------------------------------------------------------------


void __fastcall TSDIAppForm::Button1Click(TObject *Sender)
{
// Form6->Show();
void showboltz();
showboltz();
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Button2Click(TObject *Sender)
{
void manfit();
manfit();
   }

//---------------------------------------------------------------------------




void __fastcall TSDIAppForm::ToolButton11Click(TObject *Sender)
{
 Chart1->BottomAxis->Automatic=true;        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ToolButton12Click(TObject *Sender)
{
     float minay=0;
     float maxay=0;

for (int j=0;j<SDIAppForm->Chart1->SeriesCount();j++)
{

if (SDIAppForm->Chart1->Series[j]->FirstValueIndex > 0)
        {
  for (int pu=SDIAppForm->Chart1->Series[j]->FirstValueIndex;pu <= SDIAppForm->Chart1->Series[j]->LastValueIndex;pu++)
  {
  if (SDIAppForm->Chart1->Series[j]->YValues->Value[pu] > maxay) maxay= SDIAppForm->Chart1->Series[j]->YValues->Value[pu];
  }
        }
}

  SDIAppForm->Chart1->LeftAxis->Automatic=false;

  SDIAppForm->Chart1->LeftAxis->SetMinMax(minay,maxay*1.1);

 // SDIAppForm->Chart1->LeftAxis->Automatic=true;
    SDIAppForm->Chart1->Refresh();

}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ToolButton13Click(TObject *Sender)
{
 Chart1->BottomAxis->Automatic=true;
  Chart1->LeftAxis->Automatic=true;        
}
//---------------------------------------------------------------------------






void __fastcall TSDIAppForm::ToolButton4Click(TObject *Sender)
{
if (PrintDialog1 ->Execute())
{
  Chart1->Print();
}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::CopyItemClick(TObject *Sender)
{

 Graphics::TBitmap *FormImage;
 TClipboard *MyClip;

	MyClip = new TClipboard();

	FormImage = GetFormImage();
	MyClip->Assign(FormImage);

}
//---------------------------------------------------------------------------




void __fastcall TSDIAppForm::Copy2Click(TObject *Sender)
{

 Graphics::TBitmap *FormImage;
 TClipboard *MyClip;

	MyClip = new TClipboard();

	FormImage = GetFormImage();
	MyClip->Assign(FormImage);        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Shift1Click(TObject *Sender)
{
Form11->Show();
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ShowSingle1Click(TObject *Sender)
{
Form12->Show();
}
//---------------------------------------------------------------------------





void __fastcall TSDIAppForm::Series4Click(TChartSeries *Sender,
      int ValueIndex, TMouseButton Button, TShiftState Shift, int X, int Y)
{
 if (Button==mbRight && Shift.Contains(ssShift))
 {
 SDIAppForm->Series4->Delete(ValueIndex);
  Form6->Table1->RecNo=ValueIndex+1;
    Form6->Table1->Delete();
      Form6->Table1->Refresh();
  Series4->XValues->Order = loAscending;
/*
 TLocateOptions Opts;
  Opts.Clear();
   Opts << loPartialKey << loCaseInsensitive;
  Edit4->Text=FormatFloat("#0000.00",Series4->XValues->Value[ValueIndex]);
 if (Form6->Table1->Locate("wavelen",Edit4->Text.c_str(),Opts))
 {
            Form6->Table1->Delete();
            SDIAppForm->Series4->Delete(ValueIndex);
            Form6->Table1->Refresh();
            goto br;
 }
  else if (Form6->Table1->Locate("fitwavelen",Edit4->Text.c_str(),Opts))
  {
       Form6->Table1->Delete();
            SDIAppForm->Series4->Delete(ValueIndex);
            Form6->Table1->Refresh();
            goto br;
   }
   else if (Form6->Table1->Locate("wavelen",Series4->XValues->Value[ValueIndex],Opts))
 {
           Form6->Table1->Delete();
            SDIAppForm->Series4->Delete(ValueIndex);
            Form6->Table1->Refresh();
            goto br;
 }
  else if (Form6->Table1->Locate("fitwavelen",Series4->XValues->Value[ValueIndex],Opts))
  {
       Form6->Table1->Delete();
            SDIAppForm->Series4->Delete(ValueIndex);
            Form6->Table1->Refresh();
            goto br;
   }
 else
 {
 SDIAppForm->Series4->Delete(ValueIndex);
goto br;
 }
 br:
 Series4->XValues->Order = loAscending;
 */
   }

}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Button4Click(TObject *Sender)
{
Form6->Show();
}
//---------------------------------------------------------------------------


void __fastcall TSDIAppForm::FileOpenItemClick(TObject *Sender)
{
void openfile(AnsiString nomefile);
  OpenDialog->FileName = "";
     OpenDialog->Filter = "Mechelle Files (*.mch)|*.MCH|All Files (*.*)|*.*";
    AnsiString fp;
     OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
    if (OpenDialog->Execute())
  {
  SaveDialog->FileName = OpenDialog->FileName;
   fp=(ExtractFilePath(OpenDialog->FileName));
  SDIAppForm->Edit14->Text=fp;
  openfile(OpenDialog->FileName);
  }
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::FileSaveItemClick(TObject *Sender)
{
TVarRec vrs[1];
          char stringa[80]="The file already exists. Overwrite?";
	if (SaveDialog->Execute())
	{
    
		if (FileExists(SaveDialog->FileName))
		{
			if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
				mbCancel, 0) != IDYES)
                              {
				return;
                                  }
                              else
                             {
                              	 DeleteFile(SaveDialog->FileName);
                              }
		}

  FILE *out;

   out = fopen((SaveDialog->FileName).c_str(), "w");
        int w;

      for (w=Series1->FirstValueIndex;w<Series1->LastValueIndex+1;w++)
      {
        fprintf(out,"%f %f\n", Series1->XValues->Value[w], Series1->YValues->Value[w]);
      }
         fclose(out);
	}
}
//---------------------------------------------------------------------------


void __fastcall TSDIAppForm::FileExitItemClick(TObject *Sender)
{
  Close();
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::HelpAboutItemClick(TObject *Sender)
{

    const AnsiString InfoStr[10] = {"CompanyName", "FileDescription", "FileVersion", "InternalName", "LegalCopyright", "LegalTradeMarks", "OriginalFileName", "ProductName", "ProductVersion", "Comments"};
  char *ExeName = Application->ExeName.c_str();
  DWORD n,size=0;
  n = GetFileVersionInfoSize(ExeName, &size);

  if (n > 0)
  {
    char *pBuf = (char *) malloc(n);
    GetFileVersionInfo(ExeName, 0, n, pBuf);
 
      DWORD *pValue;
      unsigned int Len;
      AnsiString temp = "StringFileInfo\\041004E4\\ProductVersion";
  if (VerQueryValue(pBuf, temp.c_str(), (LPVOID *)&pValue, &Len))

        {
        AboutBox->Version->Caption= "Version " + StrPas(PChar(pValue));
        }
    free(pBuf);
  }


  AboutBox->ShowModal();
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::SavewithLabels1Click(TObject *Sender)
{

TVarRec vrs[1];
          char stringa[80]="The file already exists. Overwrite?";
	if (SaveDialog->Execute())
	{
    SaveDialog->Title="Save with Labels";
    SaveDialog->Filter="ASCII with Labels|*.LAB";
     
		if (FileExists(SaveDialog->FileName))
		{
			if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
				mbCancel, 0) != IDYES)
				{
				return;
                                  }
                              else
                             {
                              	 DeleteFile(SaveDialog->FileName);
                              }
		}

  FILE *out;

   out = fopen((SaveDialog->FileName).c_str(), "w");

         int i=0;
        int w,lg;
        AnsiString ppp;
       AnsiString spe,io;
       char la[8];
      Series4->XValues->Order = loAscending;
      for (w=Series1->FirstValueIndex;w<Series1->LastValueIndex+1;w++)
      {
       if (i < Series4->LastValueIndex+1)
    {
       if (Series4->XValues->Value[i] < Series1->XValues->Value[w])
      {
       ppp=Series4->XLabel[i];
       lg=StrLen(ppp.c_str());
     if (lg==0)
     {
     fprintf(out,"%f %f\n", Series1->XValues->Value[w], Series1->YValues->Value[w]);
     }
       else if (lg >0 && lg < 6)
  {
       AnsiString sp=ppp.SubString(lg-1,2);
       if (sp != "II")
 {
  spe=ppp.SubString(1,lg-1);
 io=AnsiString("I");
  }
  else if ((sp=="II") & (lg==2))
 {
    spe="I";
     io=AnsiString("I");
 }
 else
 {
 spe=ppp.SubString(1,lg-2);
 io=AnsiString("II");
 }
 sprintf(la,"%s%s",Trim(spe),Trim(io));
 fprintf(out,"%f %f %s \n", Series1->XValues->Value[w], Series1->YValues->Value[w],la);
       i++;
 }
 else
 {
fprintf(out,"%f %f %s \n", Series1->XValues->Value[w], Series1->YValues->Value[w],Series4->XLabel[i]);
       i++;
 }
 }
 else
      {
       fprintf(out,"%f %f\n", Series1->XValues->Value[w], Series1->YValues->Value[w]);
      }
      }
      else
      {
       fprintf(out,"%f %f\n", Series1->XValues->Value[w], Series1->YValues->Value[w]);
      }
      }
         fclose(out);
	}
}
//---------------------------------------------------------------------------

void readini()
{
SDIAppForm->Chart1->Visible=true;
AnsiString fn=ExtractFilePath(Application->ExeName)+"lips++.ini";
char pop[30];
 char pp[300];
   float fl;
   int i;
int handle;

   FILE *out;

   /* open a file */
   handle = open(fn.c_str(),S_IREAD);

   /* now turn the handle into a stream */
   out = fdopen(handle,"rt");

   if (out == NULL)
     ShowMessage("Open failed");
   else
   {

    fscanf(out,"%s // Username\n",&pp);
if (strcmp(pp,"none")== 0) {OKBottomDlg->Edit13->Text="";}
 else {OKBottomDlg->Edit13->Text=pp;}

    fscanf(out,"%f // Resolution\n",&fl);
    sprintf(pop,"%1.1f",fl);
   OKBottomDlg->Edit2->Text=pop;

    fscanf(out,"%f // Limit Low\n",&fl);
 OKBottomDlg->Edit3->Text=fl;

   fscanf(out,"%f // Limit High\n", &fl);
  OKBottomDlg->Edit4->Text=fl;

   fscanf(out,"%i // SG Points\n", &i);
   OKBottomDlg->Edit5->Text=i;

   fscanf(out,"%i // SG Order\n", &i);
   OKBottomDlg->Edit6->Text=i;

   fscanf(out,"%i // SG Der\n", &i);
   OKBottomDlg->Edit1->Text=i;

    fscanf(out,"%f // Thresh.\n", &fl);
      sprintf(pop,"%1.1f",fl);
    OKBottomDlg->Edit7->Text=pop;

   fscanf(out,"%f // Delta min.\n", &fl);
     sprintf(pop,"%1.1f",fl);
     OKBottomDlg->Edit8->Text=pop;

   fscanf(out,"%f // Range\n", &fl);
     sprintf(pop,"%1.1f",fl);
   OKBottomDlg->Edit9->Text=pop;

    fscanf(out,"%i // Apply normalization\n", &i);
     OKBottomDlg->CheckBox2->Checked=i;

       fscanf(out,"%i // Apply before\n", &i);
     OKBottomDlg->RadioButton1->Checked=i;

         fscanf(out,"%i // Apply after\n", &i);
     OKBottomDlg->RadioButton2->Checked=i;

   fscanf(out,"%s // Normalization\n", &pp);
if (strcmp(pp,"none")== 0) {OKBottomDlg->Edit10->Text="";}
 else {OKBottomDlg->Edit10->Text=pp;}


   fscanf(out,"%i // Apply singlefile\n", &i);
   OKBottomDlg->CheckBox1->Checked=i;

   fscanf(out,"%s // Single file\n", &pp);
   if (strcmp(pp,"none")==0) OKBottomDlg->Edit11->Text="";
  else OKBottomDlg->Edit11->Text=pp;

   fscanf(out,"%f // Accuracy\n", &fl);
     sprintf(pop,"%1.4f",fl);
    OKBottomDlg->Edit12->Text=pop;

   fscanf(out,"%f // Instr. width\n", &fl);
     sprintf(pop,"%1.1f",fl);
   OKBottomDlg->Edit16->Text=pop;

   fscanf(out,"%i // Fix wg\n", &i);
   OKBottomDlg->CheckBox5->Checked=i;

    fscanf(out,"%f // Fixed wg\n", &fl);
      sprintf(pop,"%1.2f",fl);
    OKBottomDlg->Edit14->Text=pop;

    fscanf(out,"%i // Fix wl\n", &i);
     OKBottomDlg->CheckBox6->Checked=i;

   fscanf(out,"%f // Fixed wl\n", &fl);
     sprintf(pop,"%1.2f",fl);
   OKBottomDlg->Edit15->Text=pop;

    fscanf(out,"%f // Aki thres.\n", &fl);
     sprintf(pop,"%1.1f",fl);
    OKBottomDlg->Edit17->Text=pop;

    fscanf(out,"%e // Ne low\n", &fl);
      sprintf(pop,"%1.2e",fl);
    OKBottomDlg->Edit18->Text=pop;

   fscanf(out,"%e // Ne high\n", &fl);
      sprintf(pop,"%1.2e",fl);
    OKBottomDlg->Edit19->Text=pop;

    fscanf(out,"%f // kT low\n", &fl);
         sprintf(pop,"%1.1f",fl);
    OKBottomDlg->Edit20->Text=pop;

   fscanf(out,"%f // kT high\n", &fl);
        sprintf(pop,"%1.1f",fl);
   OKBottomDlg->Edit21->Text=pop;

      fscanf(out,"%i // Show progress\n", &i);
      OKBottomDlg->CheckBox3->Checked=i;

         fscanf(out,"%i // Gaussian Autofit\n\n", &i);
      OKBottomDlg->CheckBox9->Checked=i;

       fscanf(out,"%i // Fix wavel.\n", &i);
       OKBottomDlg->CheckBox4->Checked=i;

        fscanf(out,"%i // Convert to A\n", &i);
        OKBottomDlg->CheckBox7->Checked=i;

         fscanf(out,"%i // Iterations\n", &i);
         OKBottomDlg->Edit22->Text=i;

         fscanf(out,"%i // Auto Offset\n", &i);
        OKBottomDlg->CheckBox8->Checked=i;

         fscanf(out,"%f // Auto Shift\n", &fl);
                sprintf(pop,"%1.2f",fl);
        OKBottomDlg->Edit23->Text=pop;

           fscanf(out,"%f // Error\n", &fl);
                sprintf(pop,"%3.2f",fl);
        OKBottomDlg->Edit24->Text=pop;
     
       if (OKBottomDlg->CheckBox1->Checked==true && FileExists(OKBottomDlg->Edit11->Text))
   {
   Form12->Series1->Clear();
 float xf,yf;

Form12->Series1->Clear();

   FILE *strm;
  strm = fopen(OKBottomDlg->Edit11->Text.c_str(), "rt");
   int idx=0;
 do
   {
   idx++;
   fscanf(strm,"%g %g", &xf, &yf);

   Form12->Series1->AddXY(idx,yf,' ',clBlack);
    }
while(!feof(strm));
   fclose(strm);
   }

  if (OKBottomDlg->CheckBox2->Checked==true && FileExists(OKBottomDlg->Edit10->Text))
  {
  float xf,yf;

Form10->Series1->Clear();

   FILE *strm;
  strm = fopen(OKBottomDlg->Edit10->Text.c_str(), "rt");
 do
   {
   fscanf(strm,"%g %g", &xf, &yf);
     if ((OKBottomDlg->CheckBox7->Checked==true) & (xf < 1500.0))
  {
    xf=xf*10.0;
  }
   Form10->Series1->AddXY(xf,yf,' ',clBlack);
    }
while(!feof(strm));
   fclose(strm);
}
else
{
   Form10->Series1->Clear();
   Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
   Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
}
  fclose(out);
   }

}
//---------------------------------------------------------------------------
void __fastcall TSDIAppForm::Offset1Click(TObject *Sender)
{
Form4->Show();
}
//---------------------------------------------------------------------------
 void loadtempl(AnsiString nome)
 {

 Form6->Table1->Active=false;
  Form6->Query1->Active=false;
  Form6->Table1->TableType=ttParadox;
  Form6->Table1->TableName=nome;
   Form6->Table1->Active=true;
     Form6->Query1->Active=true;
       float soglia=atof(OKBottomDlg->Edit17->Text.c_str());
  float pp=1.0;
   char sqls[300];
  sprintf(sqls,"select * from '%s' order by templint",nome);
   Form6->Query1->SQL->Clear();
 Form6->Query1->SQL->Add(sqls);
 Form6->Query1->Open();
 Form6->Query1->Last();
 float maxim=Form6->Query1->FieldValues["templint"];
sprintf(sqls,"SELECT * FROM '%s' ORDER BY WAVELEN",Form6->Table1->TableName.c_str());
 Form6->Query1->SQL->Clear();
 Form6->Query1->SQL->Add(sqls);
 Form6->Query1->Open();
 Form6->Query1->First();
 Form6->Caption="Active Template:"+nome;
  SDIAppForm->Series4->Clear();
     float myp;
  if (SDIAppForm->Series1->MaxYValue()  != SDIAppForm->Series1->MinYValue() )
   {
    myp= SDIAppForm->Series1->MaxYValue();
   }
   else
   {
    myp=1.0;
   }


  char lab[300];
  Form6->Table1->First();
  SDIAppForm->Series4->XValues->Order = loNone;

  for (int i=0; i < Form6->Table1->RecordCount; i++)
  {

  int ioniz=Form6->Table1->FieldByName("ion")->AsInteger;
    if (ioniz != 0)
    {
  switch(ioniz)
  {
  case 1:
  sprintf(lab,"%s I",Form6->Table1->FieldByName("specie")->AsString);
   break;
  case 2:
     sprintf(lab,"%s II",Form6->Table1->FieldByName("specie")->AsString);
  break;
  }
  if (Form6->Table1->FieldByName("Aki")->AsFloat > soglia)
  {
   SDIAppForm->Series4->AddXY(Form6->Table1->FieldValues["wavelen"],Form6->Table1->FieldValues["templint"],lab,clYellow);
   }
   else
   {
    SDIAppForm->Series4->AddXY(Form6->Table1->FieldValues["wavelen"],Form6->Table1->FieldValues["templint"],lab,COLORE);
   }
    }
     else
    {
   sprintf(lab,"%4.2f",Form6->Table1->FieldByName("wavelen")->AsFloat);
   SDIAppForm->Series4->AddXY(Form6->Table1->FieldValues["wavelen"],Form6->Table1->FieldValues["templint"],lab,clBlue);
   }
 Form6->Table1->Next();
  }
  SDIAppForm->Series4->XValues->Order = loAscending;
  Form6->Table1->First();
  SDIAppForm->Edit5->Text=1;
  Form6->DBNavigator1->Enabled=true;



// apertura correzioni

AnsiString fn = ChangeFileExt(nome,".cor");
 char ppp[300];


  FILE *in;


   if (FileExists(fn.c_str())==false){ShowMessage("Template information file doesn't exist. Select it manually in the Options window");
                                        Form3->Edit2->Text="";
                                        Form3->Edit3->Text="";
                                        Form3->Version->Text="";
                                        Form3->Edit5->Text="";
                                        Form3->Edit6->Text="";
                                        Form3->Memo1->Lines->Text="";
                                        }
   else
  {
    in = fopen(fn.c_str(),"rt");

    TMsgDlgButtons msbut;
        msbut.Clear();
         msbut << mbYes << mbCancel;

    fscanf(in,"Global Correction: %s", &ppp);
    if(strcmp(ppp,"NO")!=0)     {
                                if (FileExists(ppp)){OKBottomDlg->Edit10->Text=ppp;
                                                        Form3->Edit5->Text=ppp;
                                                        }
                                else    {

                                       if (MessageDlg("The Global Correction file " + StrPas(ppp) + " \n can't be found. Select it manually ?", mtWarning, msbut, 0)== 6)
                                                {

                                                SDIAppForm->OpenDialog2->FileName=ppp;
                                                SDIAppForm->OpenDialog2->InitialDir=ExtractFilePath(Application->ExeName);
                                                if (SDIAppForm->OpenDialog2->Execute()){
                                                              OKBottomDlg->Edit10->Text= SDIAppForm->OpenDialog2->FileName;
                                                              Form3->Edit5->Text=ppp;
                                                              }
                                                }



                                        }
                                }
    fscanf(in,"\nSingle File Correction: %s", &ppp);
    if(strcmp(ppp,"NO")!=0) {
                                if (FileExists(ppp))    {OKBottomDlg->Edit11->Text=ppp;
                                                        Form3->Edit6->Text=ppp;
                                                        }
                                else  {

                                       if (MessageDlg("The Single Correction file " + StrPas(ppp) + " \n can't be found. Select it manually ?", mtWarning, msbut, 0)== 6)
                                                {

                                                SDIAppForm->OpenDialog2->FileName=ppp;
                                                SDIAppForm->OpenDialog2->InitialDir=ExtractFilePath(Application->ExeName);
                                                if (SDIAppForm->OpenDialog2->Execute()){
                                                              OKBottomDlg->Edit11->Text= SDIAppForm->OpenDialog2->FileName;
                                                              Form3->Edit6->Text=ppp;
                                                              }
                                                }



                                        }
                             }

    fscanf(in,"\nCorrection %s integral calculation", &ppp);
    Form3->Label6->Caption=ppp;
    fscanf(in,"\nSpectrum Filename: %s", &ppp);
        if(strcmp(ppp,"none")!=0)Form3->Edit2->Text=ppp;
        else Form3->Edit2->Text="";
    fscanf(in,"\nUser: %s", &ppp);
        if(strcmp(ppp,"none")!=0)Form3->Edit1->Text=ppp;
        else Form3->Edit1->Text="";
    fscanf(in,"\nVersion: %s", &ppp);
    Form3->Version->Text=ppp;
    fscanf(in,"\nCreated Date: %s", &ppp);
    Form3->Edit3->Text=ppp;
    char notes[300]="";
    char buf[20]="";
    fscanf(in,"\nNotes:");
    do {strcat(notes,buf);
        strcat(notes," ");}
    while (fscanf(in,"%s", &buf)!=EOF);

    Form3->Memo1->Lines->Text=notes;


    fclose(in);
  }

  }
//---------------------------------------------------------------------------
 void identif(float xx)
 {
  float yy;
for (int w=SDIAppForm->Series1->FirstValueIndex;w<SDIAppForm->Series1->LastValueIndex;w++)
{
 if (SDIAppForm->Series1->XValues->Value[w] > xx)
 {
 yy=SDIAppForm->Series1->YValues->Value[w]+
(SDIAppForm->Series1->YValues->Value[w-1]-SDIAppForm->Series1->YValues->Value[w])/
(SDIAppForm->Series1->XValues->Value[w-1]-SDIAppForm->Series1->XValues->Value[w])*
(xx-SDIAppForm->Series1->XValues->Value[w]);
 goto aaa;
 }
 }
aaa:

 Form6->Show();
Form6->Table1->Active=true;
int reco;
if (Form6->Table1->RecordCount == 0)
{
 Form6->Table1->Append();
     Form6->Table1->FieldValues["wavelen"]=xx;
     Form6->Table1->FieldValues["asswavelen"]=xx;
      Form6->Table1->FieldValues["templint"]=yy;
            Form6->Table1->Post();

    char wavel[7];
     sprintf(wavel,"%4.2f",xx);
      SDIAppForm->Series4->AddXY(xx,yy,wavel,clBlue);
     SDIAppForm->Series4->XValues->Order = loAscending;
}
 else
{
Form6->Table1->First();
for (int w=0;w<Form6->Table1->RecordCount;w++)
{
float zz= Form6->Table1->FieldValues["wavelen"];
if (xx < zz)
{
     char wavel[7];
     sprintf(wavel,"%4.2f",xx);
      SDIAppForm->Series4->AddXY(xx,yy,wavel,clBlue);
     SDIAppForm->Series4->XValues->Order = loAscending;
     Form6->Table1->Insert();
     Form6->Table1->FieldValues["wavelen"]=xx;
     Form6->Table1->FieldValues["asswavelen"]=xx;
      Form6->Table1->FieldValues["templint"]=yy;
            Form6->Table1->Post();
       reco=Form6->Table1->RecNo;
     goto bbb;
 }
 else
 {
 Form6->Table1->Next();
 }
 }
 Form6->Table1->Append();
     Form6->Table1->FieldValues["wavelen"]=xx;
     Form6->Table1->FieldValues["asswavelen"]=xx;
      Form6->Table1->FieldValues["templint"]=yy;
            Form6->Table1->Post();
         Form6->Table1->RecNo=reco;   
     char wavel[7];
     sprintf(wavel,"%4.2f",xx);
      SDIAppForm->Series4->AddXY(xx,yy,wavel,clBlue);
     SDIAppForm->Series4->XValues->Order = loAscending;
 bbb:
 }
 }
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Batchprocess1Click(TObject *Sender)
{
void openfile(AnsiString nomefile);
void loadtempl(AnsiString nome);
void autofit(float jmin, float jmax, int j);
void showboltz();
void calcola();
void report(AnsiString nomerep, AnsiString nomefil, AnsiString nometemp);

 SDIAppForm->OpenDialog1->Title="Open Template for Batch Process";
 SDIAppForm->OpenDialog1->Filter = "Templates|*.DB";
 SDIAppForm->OpenDialog1->FileName = "*.DB";
 SDIAppForm->OpenDialog1->InitialDir=ExtractFilePath(Application->ExeName)+"Templates";
 AnsiString nometempl;
  if (SDIAppForm->OpenDialog1->Execute())
  {
 nometempl = SDIAppForm->OpenDialog1->FileName;
 }
 Form9->ShowModal();
 int handle;
   SDIAppForm->OpenDialog->Title="Open Files for Batch Process";
    SDIAppForm->OpenDialog->Filter = "Mechelle files|*.MCH";
OpenDialog->FileName = "*.MCH";
 OpenDialog->Options << ofAllowMultiSelect;
  if (OpenDialog->Execute())
  {
  Memo2->Lines=OpenDialog->Files;
 }

 for (int j=0; j < Memo2->Lines->Count ; j++)
  {
 AnsiString fn;
 AnsiString xx="x";
  AnsiString yy="y";
   AnsiString mch=".mch";
   AnsiString sac=" ";
 /*
 for (int i=atof(Edit7->Text.c_str()); i < atof(Edit8->Text.c_str()); i++)
 {
  for (int j=atof(Edit9->Text.c_str()); j < atof(Edit10->Text.c_str()); j++)
  {
*/
//  fn=xx+i+yy+j+mch;
 SDIAppForm->Show();
 openfile(SDIAppForm->Memo2->Lines->Strings[j]);
// openfile(fn);
  SDIAppForm->Chart1->Refresh();
  loadtempl(nometempl);
  SDIAppForm->Chart1->Refresh();
  float tim;
  for (int q=0; q < 10000; q++)
  {
  tim=q*245.21-32+q/2341.23;
  SDIAppForm->Edit6->Text=q;
  }
  float jmin,jmax;
  int j;
autofit(jmin,jmax,j);
Form6->Table1->Refresh();
Form9->Show();
  for (int q=0; q < 10000; q++)
  {
  tim=q*245.21-32+q/2341.23;
  SDIAppForm->Edit6->Text=q;
  }
  showboltz();
     Form9->Chart1->Refresh();

/*
 Form9->RadioGroup1->ItemIndex=3;
  Form9->RadioGroup2->ItemIndex=3;
  Form9->ComboBox1->ItemIndex=5;
  Form9->ComboBox2->ItemIndex=4;
  */
  for (int q=0; q < 10000; q++)
  {
  tim=q*245.21-32+q/2341.23;
  SDIAppForm->Edit6->Text=q;
  }
  calcola();
 /*
 float tmpmg= atof(Form9->StringGrid1->Cells[3][6].c_str());
 float nemg= atof(Form9->StringGrid2->Cells[4][5].c_str());

  Form9->RadioGroup1->ItemIndex=2;
  Form9->RadioGroup2->ItemIndex=2;
   Form9->Edit1->Text=tmpmg;
   Form9->Edit2->Text=nemg;
  Form9->Chart1->Refresh();
    for (int q=0; q < 10000; q++)
  {
  tim=q*245.21-32+q/2341.23;
  SDIAppForm->Edit6->Text=q;
  }
  calcola();
 */
  Form9->Refresh();

     Form9->Chart1->Refresh();
     for (int q=0; q < 10000; q++)
  {
  tim=q*245.21-32+q/2341.23;
  SDIAppForm->Edit6->Text=q;
  }

  AnsiString ppp=SDIAppForm->Memo2->Lines->Strings[j];
 AnsiString io;
int lg=StrLen(ppp.c_str());
  AnsiString sp=ppp.SubString(0,lg-3);
  io="rep";
   AnsiString www=sp+io;
//  AnsiString pp=sac+i+sac+j;
  report(www,SDIAppForm->Memo2->Lines->Strings[j],nometempl);
 // report(www,pp,nometempl);
 // }
}
   ShowMessage("Done");
}
//---------------------------------------------------------------------------
 void openfile(AnsiString nomefile)
 {
 int handle;

  SDIAppForm->Series1->Clear();
  SDIAppForm->Series2->Clear();
   SDIAppForm->Series3->Clear();
    SDIAppForm->Series4->Clear();
//  SDIAppForm->Series5->Clear();

 SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;
   


   double wave;
   double lips;
   float yyy;
   FILE *stream;
  SDIAppForm->Caption = "Opening File:" + nomefile;
  SDIAppForm->StatusBar->SimpleText="LIBS++ Software for Spectral Analysis (c) 1999-2005 Applied Laser Spectroscopy Laboratory @ IPCF-CNR";
  Form13->StringGrid1->Cells[1][0]=nomefile;
  Form13->StringGrid1->Refresh();
  SDIAppForm->Edit9->Text = nomefile;
  handle = open((nomefile).c_str(),O_RDONLY);
  stream = fdopen(handle, "r");
   SDIAppForm->Series1->XValues->Order = loAscending;

  do
   {
   fscanf(stream,"%le %le", &wave, &lips);
    if ((OKBottomDlg->CheckBox7->Checked==true) & (wave < 1500))
    wave=wave*10;
   if ((wave <= atof(OKBottomDlg->Edit4->Text.c_str()))  & (wave >= atof(OKBottomDlg->Edit3->Text.c_str())))
  {
  SDIAppForm->Series1->AddXY(wave+atof(OKBottomDlg->Edit23->Text.c_str()),lips,' ',clBlack);
  }
 else
 {
 }
 }
   while (!eof(handle));
   close(handle);

   float ofs;
  if  (OKBottomDlg->CheckBox8->Checked==true)
  {

  ofs=SDIAppForm->Series1->YValues->MinValue;
   for (int i=0; i < SDIAppForm->Series1->Count(); i++)
  {
   SDIAppForm->Series1->YValues->Value[i]-=ofs;
   }
  }

if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton1->Checked==true)
 {
 for (int i=0; i < SDIAppForm->Series1->Count(); i++)
 {
 wave=SDIAppForm->Series1->XValues->Value[i];

  for (int k=1; k < Form10->Series1->Count(); k++)
{
 if (wave < Form10->Series1->XValues->Value[k])
{
yyy=Form10->Series1->YValues->Value[k]+
(Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
(Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
(wave-Form10->Series1->XValues->Value[k]);
SDIAppForm->Series1->YValues->Value[i]/=yyy;
 break;
 }
}

}

SDIAppForm->Series1->Active=true;
SDIAppForm->Series1->XValues->Order = loAscending;
}

    AnsiString fn=ExtractFilePath(Application->ExeName)+"\Templates\\template.db";
   Form6->Table1->Active = false;
    Form6->Table1->TableName=fn;
    Form6->Table1->EmptyTable();
    Form6->Table1->Active = true;

   SDIAppForm->Caption = "Current File:" + ExtractFileName(nomefile);
   SDIAppForm->Edit5->Text=1;
  }
//---------------------------------------------------------------------------
 void autofit(float jmin, float jmax, int j)
 {
 double integrale(float x, float w[]);
  int colo[34]={clWhite,clRed,clYellow,clGreen,clMaroon,clDkGray,clOlive,clPurple,clLtGray,clBlue,clNavy,clBlack,clFuchsia,clGray,clTeal,clSilver,clLime,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
  void gauss(float x, float a[], float *y, float dyda[], int na);
void voigt(float x, float a[], float *y, float dyda[], int na);
void plotvoigt(float x, float a[], float *y, int na);
void free_matrix(float **m, long nrl, long nrh, long ncl, long nch);
void free_vector(float *v, long nl, long nh);
void free_ivector(int *v, long nl, long nh);
void manfit();

 float *vector(long nl,long nh);
  int *ivector(long nl,long nh);

       Form14->Image2->Visible=false;
            Form14->Image1->Visible=false;
            Form14->Image3->Visible=false;

float y,*a,*origa,*chi;
float *dyda,delta0,delta,accu;
int k,group,na,oldj,upoints,*ia;

// Form6->Show();
 Form6->Table1->Refresh();
 Form6->Table1->First();

delta0=atof((OKBottomDlg->Edit8->Text).c_str());
accu=atof((OKBottomDlg->Edit12->Text).c_str());
SDIAppForm->Chart1->BottomAxis->Automatic=false;
    Form14->Edit2->Text="";
  float **covar,**alpha;
            float chisq,*xx,*z,*sg,oldchisq,ran;
             float alamda,maxax,minax,maxay,minay,firstin,lastin;
             int g;
      minay=0;
     SDIAppForm->Series1->Active=true;
     SDIAppForm->Series3->Active=true;
     SDIAppForm->Series4->Active=true;
// for (j=jmin;j<=jmax;j++)
// {
  group=1;
  oldj=j;
  delta= delta0*(SDIAppForm->Series4->XValues->Value[oldj])/5000.;
  minax=SDIAppForm->Series4->XValues->Value[oldj]-delta;
  maxax=SDIAppForm->Series4->XValues->Value[oldj]+delta;
 while (j<SDIAppForm->Series4->Count()-1 && SDIAppForm->Series4->XValues->Value[j+1] < (maxax+delta))
  {
  group++;
  j++;
  maxax=SDIAppForm->Series4->XValues->Value[j]+delta;
  }

    SDIAppForm->Edit12->Text=j;
     SDIAppForm->Chart1->BottomAxis->SetMinMax(minax,maxax);

  SDIAppForm->Chart1->Refresh();

     minay=0;
      maxay=0;

for (int j=0;j<SDIAppForm->Chart1->SeriesCount();j++)
{
if (SDIAppForm->Chart1->Series[j]->FirstValueIndex > 0)
        {
  for (int pu=SDIAppForm->Chart1->Series[j]->FirstValueIndex;pu <= SDIAppForm->Chart1->Series[j]->LastValueIndex;pu++)
  {
  if (SDIAppForm->Chart1->Series[j]->YValues->Value[pu] > maxay) maxay= SDIAppForm->Chart1->Series[j]->YValues->Value[pu];
  }
        }
}

  SDIAppForm->Chart1->LeftAxis->Automatic=false;

  SDIAppForm->Chart1->LeftAxis->SetMinMax(minay,maxay*1.1);

 // SDIAppForm->Chart1->LeftAxis->Automatic=true;
    SDIAppForm->Chart1->Refresh();

 //  }

  //  SDIAppForm->Chart1->BottomAxis->Automatic=true;
  //  SDIAppForm->Chart1->LeftAxis->Automatic=true;

   }
//---------------------------------------------------------------------------
void calcola()
{

double zZ(AnsiString spp,int ion,float ti);
void fit(float x[], float y[], int ndata, float sig[], int mwt, float *a, float *b, float *siga, float *sigb, float *chi2, float *q);
float rtbis(double (*func)(double), double x1, double x2, float xacc);
double test(double x);
int colo[34]={clRed,clGray,clYellow,clBlue,clGreen,clBlack,clMaroon,clNavy,clOlive,clPurple,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
Form9->Edit10->Text="0";
Form9->Edit8->Text="";
if (Form9->RadioGroup2->ItemIndex !=2)
        {
        Form9->Edit2->Text="1.E18";
        }
float soglia=atof(OKBottomDlg->Edit17->Text.c_str());
Form9->Chart1->BottomAxis->Automatic=true;
Form9->Chart1->LeftAxis->Automatic=true;
Form9->StringGrid1->RowCount=128;
Form9->StringGrid2->RowCount=64;

// Inizio plot
Form9->Query1->Active=false;
Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query2->Active=false;
Form9->Query2->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query3->Active=false;
Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query6->Active=false;
Form9->Query6->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query1->Active=true;
Form9->Query2->Active=true;
Form9->Query3->Active=true;
Form9->Query6->Active=true;

int I, J;

for (I = 1; I < Form9->StringGrid1->ColCount; I++)
    for (J = 1; J < Form9->StringGrid1->RowCount; J++)
      Form9->StringGrid1->Cells[I][J] = "";
  for (I = 2; I < Form9->StringGrid2->ColCount; I++)
    for (J = 1; J < Form9->StringGrid2->RowCount; J++)
      Form9->StringGrid2->Cells[I][J] = "";

double xs,ys,yqs,xqs,xy,errore,delta,kt,q,us,eq;

char sqls[300];
int progre=0;
sprintf(sqls,"SELECT DISTINCT specie,ion FROM %s WHERE aki !=0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",ExtractFileName(Form6->Table1->TableName));
Form9->Query1->SQL->Clear();
Form9->Query1->SQL->Add(sqls);
Form9->Query1->Open();
Form9->Query1->First();
sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki !=0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie",ExtractFileName(Form6->Table1->TableName));
Form9->Query2->SQL->Clear();
Form9->Query2->SQL->Add(sqls);
Form9->Query2->Open();
Form9->Query2->First();

while (Form9->Chart1->SeriesCount()>0)
        {
        Form9->Chart1->Series[0]->Free();
        }

char sname[32];
for (int i=0; i < Form9->Query1->RecordCount; i++)
        {
        Form9->StringGrid1->Cells[0][i+1]="";
        TPointSeries *MySeries = new TPointSeries(Form9);
        MySeries->XValues->Order=loNone;
        MySeries->ParentChart=Form9->Chart1;
        Form9->Edit3->Text=Form9->Query1->FieldValues["specie"];
        Form9->Edit4->Text=Form9->Query1->FieldValues["ion"];

        int ioniz=Form9->Query1->FieldValues["ion"];
        switch(ioniz)
                {
                case 1:
                sprintf(sname,"%sI",Trim(Form9->Edit3->Text));
                break;
                case 2:
                sprintf(sname,"%sII",Trim(Form9->Edit3->Text));
                break;
                }

        Form9->StringGrid1->Cells[1][i+1]=sname;

        MySeries->Name=sname;
        MySeries->Cursor=crHandPoint;
        sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki !=0.0 AND aki != -1.0 AND inte > 0.0",ExtractFileName(Form6->Table1->TableName),Form9->Edit3->Text,Form9->Edit4->Text);
        Form9->Query3->SQL->Clear();
        Form9->Query3->SQL->Add(sqls);
        Form9->Query3->Open();
        Form9->Query3->First();

        float yyy;
        int reco= Form9->Query3->RecordCount;
        Form9->StringGrid1->Cells[2][i+1]=reco;
        for (int j=0; j < reco; j++)
                {
                progre++;
                float wave=Form9->Query3->FieldValues["wavelen"];
                float inte=Form9->Query3->FieldValues["inte"];
                float erro= Form9->Query3->FieldValues["error-inte"];
                float aki= Form9->Query3->FieldValues["aki"];
                int gk= Form9->Query3->FieldValues["gk"];
                float Ek= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
                if ((OKBottomDlg->CheckBox2->Checked==true) & (OKBottomDlg->RadioButton2->Checked==true))
                        {
                        for (int k=0; k < Form10->Series1->Count(); k++)
                                {
                                if (wave < Form10->Series1->XValues->Value[k])
                                        {
                                        yyy=Form10->Series1->YValues->Value[k]+
(Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
(Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
(wave-Form10->Series1->XValues->Value[k]);
                                        goto aaa;
                                        }
                                }
                        }
                else
                        {
                        yyy=1.0;
                        }
                float sac;
                aaa:
                if (atof(Form23->StringGrid1->Cells[3][progre].c_str())!=0)
                        {
                        sac=atof(Form23->StringGrid1->Cells[3][progre].c_str());
                        }
                else
                        {
                        sac=1.0;
                        }
                inte/=(yyy*sac);
                erro/=(yyy*sac);

                float yy=log(inte/fabs(aki*gk));
                //  float erl=erro/inte;
                float erl=0.1;
                char wa[20];
                sprintf(wa,"%4.2e",erl);

                if (aki > soglia)
                        {
                        Form9->Chart1->Series[i]->SeriesColor=colo[i];
                        Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,clTeeColor);
                        }
                else
                        {
                        Form9->Chart1->Series[i]->AddXY(Ek,yy,wa,COLORE);
                        }

                Form9->Query3->Next();
                }

        Form9->Query1->Next();
}
// Fine plot

Form9->Query1->First();
Form9->Query2->First();
int sc= Form9->Chart1->SeriesCount();
for (int i=0; i < sc; i++)
        {
        char sqls[300];
        AnsiString ppp=Form9->Chart1->Series[i]->Name;
        AnsiString spe,io;
        int lg=StrLen(ppp.c_str());
        AnsiString sp=ppp.SubString(lg-1,2);
        if (sp != "II")
                {
                spe=ppp.SubString(1,lg-1);
                io=AnsiString("1");
                }
        else if ((sp=="II") & (lg==2))
                {
                spe="I";
                io=AnsiString("1");
                }
        else
                {
                spe=ppp.SubString(1,lg-2);
                io=AnsiString("2");
                }

        sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki !=0.0 and aki !=-1.0 AND inte >0.0",ExtractFileName(Form6->Table1->TableName),spe,io);

        Form9->Query3->SQL->Clear();
        Form9->Query3->SQL->Add(sqls);
        Form9->Query3->Open();
        Form9->Query3->First();

        int reco= Form9->Query3->RecordCount;

        // Fit lineare (II versione)
        if (reco > 1)
                {
                // Costruisco i vettori
                int count=-1;

                float x[200],y[200],sig[200];
                int j;
                for (j=0;j < reco;j++)
                        {
                        if (Form9->Chart1->Series[i]->ValueColor[j] !=COLORE)
                                {
                                count++;
                                float xx= Form9->Chart1->Series[i]->XValues->Value[j];
                                float yy= Form9->Chart1->Series[i]->YValues->Value[j];
                                x[count]=xx;
                                y[count]=yy;
                            //    float errore=max(atof(Form9->Chart1->Series[i]->XLabel[j].c_str()),1.e-20);
                              float errore=1.;
                                sig[count]=errore;
                                }
                        }
                // fine

                //Se ci sono almeno due punti...
                if (count > 0)
                        {
                        int mwt=1;
                        float ktt,qq,siga,erore,chi2,r;
                        fit(x, y, count, sig, mwt, &qq, &ktt, &siga, &erore, &chi2, &r);

                        char tmd[20];
                        if (ktt==0.0)
                                {
                                ktt= 0.01;
                                }
                        kt=ktt;
                        q=qq;

                        sprintf(tmd,"%1.4f",-1.0/ktt);
                        Form9->StringGrid1->Cells[3][i+1]=tmd;
                        sprintf(tmd,"%1.4f",q);
                        Form9->StringGrid1->Cells[4][i+1]=tmd;
                        }
                else
                        {
                        }

                }
        }

// Calcolo Temperatura media
     Form9->Query1->First();
     int num=0;
     float tmed=0.0;
     float ktt;
     for (int i=0; i < Form9->Query1->RecordCount; i++)
        {
        ktt=atof(Form9->StringGrid1->Cells[3][i+1].c_str());
        if ((ktt > atof(OKBottomDlg->Edit20->Text.c_str())) & (ktt < atof(OKBottomDlg->Edit21->Text.c_str())))
                {
                int lins=atoi(Form9->StringGrid1->Cells[2][i+1].c_str());
                tmed+=lins*ktt;
                num+=lins;
                }
        Form9->Query1->Next();
        }
     if (num!=0.0)
        {
        tmed/=num;
        }
     else
        {
        tmed=atof(Form9->Edit1->Text.c_str());
        }
     char tdm[10];
     sprintf(tdm,"%1.4f",tmed);
     Form9->Edit7->Text=tdm;

     if ((tmed < atof(OKBottomDlg->Edit20->Text.c_str())) | (tmed > atof(OKBottomDlg->Edit21->Text.c_str())))
        {
        tmed=atof(Form9->Edit1->Text.c_str());
        }

   //Ricalcolo Z e q per ogni specie, con la temperatura giusta

 for (int i=0; i < Form9->Query1->RecordCount; i++)
        {
        AnsiString ppp=Form9->Chart1->Series[i]->Name;
        AnsiString spe,io;
        int lg=StrLen(ppp.c_str());
        AnsiString sp=ppp.SubString(lg-1,2);
        if (sp != "II")
                {
                spe=ppp.SubString(1,lg-1);
                io=AnsiString("1");
                }
        else if ((sp=="II") & (lg==2))
                {
                spe="I";
                io=AnsiString("1");
                }
        else
                {
                spe=ppp.SubString(1,lg-2);
                io=AnsiString("2");
                }

        // attenzione: inizio blocco 1 della Z old
        sprintf(sqls,"SELECT DISTINCT Ei,gi FROM %s WHERE ion=%s ORDER BY Ei",spe.c_str(),io.c_str());
        Form9->Query4->SQL->Clear();
        Form9->Query4->SQL->Add(sqls);
        Form9->Query4->Open();
        Form9->Query4->First();
        sprintf(sqls,"SELECT DISTINCT Ek,gk FROM %s WHERE ion=%s ORDER BY Ek",spe.c_str(),io.c_str());
        Form9->Query8->SQL->Clear();
        Form9->Query8->SQL->Add(sqls);
        Form9->Query8->Open();
        Form9->Query8->First();
        //fine blocco 1 della Z old

        //Scelgo la temperatura
        float kappati;
        switch (Form9->RadioGroup1->ItemIndex)
                {
                case 0:
                kappati=atof(Form9->StringGrid1->Cells[3][i+1].c_str());
                break;
                case 1:
                kappati=tmed;
                break;
                case 2:
                kappati=atof(Form9->Edit1->Text.c_str());
                break;
                case 3:
                int ix=Form9->ComboBox1->ItemIndex;
                kappati=atof(Form9->StringGrid1->Cells[3][ix+1].c_str());
                Form9->Edit1->Text=kappati;
                break;
                }

        if (((kappati < atof(OKBottomDlg->Edit20->Text.c_str())) | (kappati > atof(OKBottomDlg->Edit21->Text.c_str())) ) & (Form9->RadioGroup1->ItemIndex == 0))
                {
                kappati= tmed;
                }

        // Ricalcolo q per la specie

        // Form9->Chart1->BottomAxis->Automatic=false;
        //  Form9->Chart1->LeftAxis->Automatic=false;
        float ym=0.0;
        float erro=0.0;
        float erroq=0.0;
        float xm=0.0;
        float em=0.0;
        for (int p=0; p < Form9->Chart1->Series[i]->Count(); p++)
                {
                erro=max(atof(Form9->Chart1->Series[i]->XLabel[p].c_str()),1.e-20);
                erroq=erro*erro;
                if (Form9->Chart1->Series[i]->ValueColor[p] !=COLORE)
                        {
                        ym+=(Form9->Chart1->Series[i]->YValues->Value[p])/erroq;
                        xm+= Form9->Chart1->Series[i]->XValues->Value[p]/erroq;
                        em+=1.0/erroq;
                        }
                }
        char kpt[20];
        sprintf(kpt,"%1.4f",kappati);
        Form9->StringGrid1->Cells[3][i+1]=kpt;
        float nq;
        if (em != 0)
                {
                nq=(ym+xm/kappati)/em;
                }
        else
                {
                nq=0.0;
                }
        char tmd[20];
        sprintf(tmd,"%1.4f",nq);
        Form9->StringGrid1->Cells[4][i+1]=tmd;

        TLineSeries *MyLinSeries = new TLineSeries(Form9);
        MyLinSeries->ParentChart=Form9->Chart1;

        switch(atoi(io.c_str()))
                {
                case 1:
                sprintf(sname,"Fit%sI",Trim(spe));
                break;
                case 2:
                sprintf(sname,"Fit%sII",Trim(spe));
                break;
                }

        MyLinSeries->Name=sname;
        double E1=Form9->Chart1->BottomAxis->Minimum;
        double E2=Form9->Chart1->BottomAxis->Maximum;
        double y1=nq-E1/kappati;
        double y2=nq-E2/kappati;
        MyLinSeries->SeriesColor=colo[i];
        MyLinSeries->AddXY(E1,y1,' ',clTeeColor);
        MyLinSeries->AddXY(E2,y2,' ',clTeeColor);


        //Calcolo Z per la specie

        float z=0.0;
        // inizio blocco 2 della Z old
        Form9->Query4->First();
        if (Form9->Query4->FieldValues["Ei"] !=0.0)
        {
        z=1.0;
        }
        for (int j=0; j< Form9->Query4->RecordCount; j++)
        {
        float g=Form9->Query4->FieldValues["gi"];
        float e=Form9->Query4->FieldValues["Ei"];
        z+=g*exp(-e*0.000123985/kappati);
        Form9->Query4->Next();
        }

        for (int j8=0; j8< Form9->Query8->RecordCount; j8++)
        {
        float g8=Form9->Query8->FieldValues["gk"];
        float e8=Form9->Query8->FieldValues["Ek"];
        Form9->Query4->First();
        int j4;
        for (j4=0; j4< Form9->Query4->RecordCount; j4++)
        {
        float g4=Form9->Query4->FieldValues["gi"];
        float e4=Form9->Query4->FieldValues["Ei"];
        if ((e4 != e8) | ((e4 == e8) && (g4 != g8))) Form9->Query4->Next();
        else goto ot;
        }
        z+=g8*exp(-e8*0.000123985/kappati);
        ot:
        Form9->Query8->Next();
        }
        if (z == 0.0)
        {
        z=2.0+exp(-2.0/kappati);
        }
        double zold=z;



 //calcolo la funzione di partizione col nuovo database estratto da kurucz


        sprintf(sqls,"SELECT DISTINCT Ei,gi FROM livelli WHERE element='%s' AND ion='%s' ORDER BY Ei",spe,io);
        Form9->Query4->SQL->Clear();
        Form9->Query4->SQL->Add(sqls);
        Form9->Query4->Open();
        Form9->Query4->First();

        z=0.0;
        if (Form9->Query4->RecordCount>0)
                {
                if (Form9->Query4->FieldValues["Ei"] !=0.0)
                        {
                        z=1.0;
                        }
                for (int jnew=0; jnew< Form9->Query4->RecordCount; jnew++)
                        {
                        float gi=Form9->Query4->FieldValues["gi"];
                        float ei=Form9->Query4->FieldValues["Ei"];
                        z+=gi*exp(-ei*0.000123985/kappati);
                        Form9->Query4->Next();
                        }
                }
        if (z == 0.0)
                {
                z=2.0+exp(-2.0/kappati);
                }
         float zmed=z;

         int oin;
         if (io=="1") oin=1; else oin=2;
         z=zZ(spe,oin,kappati);
        sprintf(tmd,"%1.4f",z);
        Form9->StringGrid1->Cells[5][i+1]=tmd;
         sprintf(tmd,"la Z di %s col vecchio metodo, a T = %1.4f : %1.4f . Dal Kurucz : %1.4f . Dal Payling : %1.4f .",sname,kappati,zold,zmed,z) ;

        }

 //fine ciclo su grid 1

 //inizio ciclo del calcolo delle specie mancanti

 gltstar=atof(Form9->Edit7->Text.c_str());
 if(Form9->CheckBox1->Checked == false)

        // Calcolo con Saha-Boltzmann
        {
        //ShowMessage("entro in saha-boltzmann");
        sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0  ORDER BY specie",ExtractFileName(Form6->Table1->TableName),soglia);
        Form9->Query2->SQL->Clear();
        Form9->Query2->SQL->Add(sqls);
        Form9->Query2->Open();
        Form9->Query2->First();

        double saha,eion;
        for (int i=0; i < Form9->Query2->RecordCount;i++)
                {
                // Cerco stato neutro
                //ShowMessage(i);
                AnsiString ppp=Form9->Query2->FieldValues["specie"];
                sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=1 AND aki >0 AND inte > 0.0",ExtractFileName(Form6->Table1->TableName),ppp);
                Form9->Query6->SQL->Clear();
                Form9->Query6->SQL->Add(sqls);
                Form9->Query6->Open();
                Form9->Query6->First();
                int lin1=Form9->Query6->RecordCount;

                sprintf(sname,"%sI",Trim(ppp).c_str());

                Form9->Query1->First();
                float pop1,z1,t1;
                for (int j=0; j < Form9->Query1->RecordCount;j++)
                        {
                        if  ((Form9->StringGrid1->Cells[1][j+1]==sname))
                                {
                                t1=atof(Form9->StringGrid1->Cells[3][j+1].c_str());
                                pop1=atof(Form9->StringGrid1->Cells[4][j+1].c_str());
                                z1=atof(Form9->StringGrid1->Cells[5][j+1].c_str());
                                break;
                                }
                        Form9->Query1->Next();
                        }

                // Cerco stato ionizzato

                sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=2 AND aki >0 AND inte > 0.0",ExtractFileName(Form6->Table1->TableName),ppp);

                Form9->Query6->SQL->Clear();
                Form9->Query6->SQL->Add(sqls);
                Form9->Query6->Open();
                Form9->Query6->First();
                int lin2=Form9->Query6->RecordCount;
                sprintf(sname,"%sII",Trim(ppp).c_str());

                Form9->Query1->First();
                float pop2,z2,t2;
                for (int j=0; j < Form9->Query1->RecordCount;j++)
                        {
                        if  ((Form9->StringGrid1->Cells[1][j+1]==sname))
                                {
                                t2=atof(Form9->StringGrid1->Cells[3][j+1].c_str());
                                pop2=atof(Form9->StringGrid1->Cells[4][j+1].c_str());
                                z2=atof(Form9->StringGrid1->Cells[5][j+1].c_str());
                                break;
                                }
                        Form9->Query1->Next();
                        }

                // Se ci sono I e II calcolo Ne per l'elemento
                if ((lin1*lin2) !=0)
                        {
                        sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",Form9->StringGrid2->Cells[1][i+1]);
                        Form9->Query5->SQL->Clear();
                        Form9->Query5->SQL->Add(sqls);
                        Form9->Query5->Open();
                        eion=Form9->Query5->FieldValues["en_ion"]*0.000123985;

                        float kti;
                        switch(Form9->RadioGroup1->ItemIndex)
                                {
                                case 0:
                                kti=(t1+t2)/2.0;
                                break;
                                case 1:
                                kti=t1;
                                break;
                                case 2:
                                kti=atof(Form9->Edit1->Text.c_str());
                                break;
                                case 3:
                                kti=t1;
                                break;
                                }
                        //saha è la densità elettronica
                        saha=(6.04e+21)*exp(pop1-pop2)*pow(kti,1.5)*exp(-eion/kti);
                        double ratio=(exp(pop1)*z1)/(exp(pop2)*z2+exp(pop1)*z1);
                        char rat[20];
                        sprintf(rat,"%1.4f",ratio);
                        Form9->StringGrid2->Cells[5][i+1]=rat;
                        double conc=exp(pop1)*z1+exp(pop2)*z2;
                        char cm[10];
                        sprintf(cm,"%1.2f",conc);
                        Form9->StringGrid2->Cells[2][i+1]=cm;
                        float massa=Form9->Query5->FieldValues["m_atomica"];
                        float cmassa=massa*conc;
                        sprintf(cm,"%1.4f",cmassa);
                        Form9->StringGrid2->Cells[3][i+1]=cm;
                        }
                else
                        {
                        saha=0.0;
                        }
                char sh[10];
                sprintf(sh,"%1.4e",saha);
                Form9->StringGrid2->Cells[4][i+1]=sh;
                Form9->Query2->Next();
                }
        //fine del ciclo su i iniziato alla linea 4332 e che scorre sui diversi elementi

        //Calcolo Ne medio

        float dtt;
        Form9->Query2->First();
        int dnum=0;
        float dmed=0.0;
        for (int i=0; i < Form9->Query2->RecordCount; i++)
                {
                dtt=atof(Form9->StringGrid2->Cells[4][i+1].c_str());
                if (dtt !=0.0)
                        {
                        dmed+=dtt;
                        dnum++;
                        }
                Form9->Query2->Next();
                }
        if (dnum !=0.0)
                {
                dmed/=dnum;
                }
        else
                {
                dmed=atof(Form9->Edit2->Text.c_str());
                }

        if ((dmed < atof(OKBottomDlg->Edit18->Text.c_str())) | (dmed > atof(OKBottomDlg->Edit19->Text.c_str())))
                {
                dmed=atof(Form9->Edit2->Text.c_str());
                }

        // Ricalcolo Ne

        Form9->Query2->First();
        for (int i=0; i < Form9->Query2->RecordCount; i++)
                {
                float densel;
                switch (Form9->RadioGroup2->ItemIndex)
                        {
                        case 0:
                        densel=atof(Form9->StringGrid2->Cells[4][i+1].c_str());
                        break;
                        case 1:
                        densel=dmed;
                        break;
                        case 2:
                        densel=atof(Form9->Edit2->Text.c_str());
                        break;
                        case 3:
                        int ix=Form9->ComboBox2->ItemIndex;
                        densel=atof(Form9->StringGrid2->Cells[4][ix+1].c_str());
                        char dm1[10];
                        sprintf(dm1,"%1.2e",densel);
                        Form9->Edit2->Text=dm1;
                        break;
                        }

                if (((densel < atof(OKBottomDlg->Edit18->Text.c_str())) | (densel > atof(OKBottomDlg->Edit19->Text.c_str())) ) && (Form9->RadioGroup2->ItemIndex == 0))
                        {
                        densel=atof(Form9->Edit2->Text.c_str());
                        }

                char dm1[10];
                sprintf(dm1,"%1.2e",densel);
                Form9->StringGrid2->Cells[4][i+1]=dm1;
                Form9->Query2->Next();
                }

        char dme[10];
        sprintf(dme,"%1.2e",dmed);
        Form9->Edit8->Text=dme;
        }
 else
        {
        // Inizio Calcolo Stark
        Form20->Show();
        Form20->Table1->Open();
        if (Form20->Table1->RecordCount !=0)
                {
                Form20->StringGrid1->ColWidths[0]=20;
                Form20->StringGrid1->ColWidths[4]=60;
                Form20->StringGrid1->RowCount=2;
                Form20->StringGrid1->Cells[0][0]="Sel.";
                Form20->StringGrid1->Cells[1][0]="Species";
                Form20->StringGrid1->Cells[2][0]="Wavel.";
                Form20->StringGrid1->Cells[3][0]="W Lor.";
                Form20->StringGrid1->Cells[4][0]="Ne";

                Form20->StringGrid1->Refresh();
                Form20->StringGrid1->RowCount=max(Form20->Table1->RecordCount+1,2);
                Form20->Table1->First();
                int jjj=0;
                char lab[300];
                for (int j=0; j < Form20->Table1->RecordCount;j++)
                        {
                        float freqw = Form20->Table1->FieldByName("Wavelength")->AsFloat;
                        int ioniz=Form20->Table1->FieldByName("Ion")->AsInteger;
                        switch(ioniz)
                                {
                                case 1:
                                sprintf(lab,"%s I",Form20->Table1->FieldByName("Element")->AsString);
                                break;
                                case 2:
                                sprintf(lab,"%s II",Form20->Table1->FieldByName("Element")->AsString);
                                break;
                                }
                        char sqls[300];
                        sprintf(sqls,"SELECT * FROM '%s' where specie = '%s' and ion = %i",Form6->Table1->TableName.c_str(),Form20->Table1->FieldByName("Element")->AsString,Form20->Table1->FieldByName("Ion")->AsInteger);
                        Form6->Query1->SQL->Clear();
                        Form6->Query1->SQL->Add(sqls);
                        Form6->Query1->Open();
                        gltstar=atof(Form9->Edit7->Text.c_str());

                        if (Form6->Query1->RecordCount !=0)
                                {
                                Form6->Query1->First();

                                for (int q=0; q < Form6->Query1->RecordCount;q++)
                                        {
                                        char wa[20];
                                        sprintf(wa,"%4.2f",Form6->Query1->FieldByName("asswavelen")->AsFloat);
                                        float wwa=atof(wa);
                                        char wac[20];
                                        sprintf(wac,"%4.2f",freqw);
                                        float wwac=atof(wac);
                                        if (wwa == wwac && Form6->Query1->FieldByName("inte")->AsFloat !=0.0)
                                                {
                                                float w5000=Form20->Table1->FieldByName("w-T5000")->AsFloat;
                                                float w10000=Form20->Table1->FieldByName("w-T10000")->AsFloat;
                                                float a5000=Form20->Table1->FieldByName("a-T5000")->AsFloat;
                                                float a10000=Form20->Table1->FieldByName("a-T10000")->AsFloat;
                                                gltstar*=11600.;
                                                if (gltstar <= 5000.)
                                                        {
                                                        glaa=a5000;
                                                        glww=w5000;
                                                        }
                                                else if (gltstar >=10000.)
                                                        {
                                                        glaa=a10000;
                                                        glww=w10000;
                                                        }
                                                else
                                                        {
                                                        glaa=a5000+(a10000-a5000)*(gltstar-5000.)/5000.;
                                                        glww=w5000+(w10000-w5000)*(gltstar-5000.)/5000.;
                                                        }
                                                double nmin=log10(atof(OKBottomDlg->Edit18->Text.c_str()));
                                                double nmax=log10(atof(OKBottomDlg->Edit19->Text.c_str()));
                                                float xacc=0.0001;
                                                char sqls[300];

                                                sprintf(sqls,"SELECT * FROM '%s' where specie = '%s' and ion = %i",Form6->Table1->TableName.c_str(),Form20->Table1->FieldByName("Element")->AsString,Form20->Table1->FieldByName("Ion")->AsInteger);
                                                Form9->Query3->SQL->Clear();
                                                Form9->Query3->SQL->Add(sqls);
                                                Form9->Query3->Open();
                                                Form9->Query3->First();

                                                for (int b=0; b < Form9->Query3->RecordCount; b++)
                                                        {
                                                        if (abs(Form20->Table1->FieldByName("wavelength")->AsFloat-Form9->Query3->FieldByName("asswavelen")->AsFloat) < 0.01)
                                                                {
                                                                glwlor=Form9->Query3->FieldByName("wl")->AsFloat;
                                                                double wgau=Form9->Query3->FieldByName("wg")->AsFloat;
                                                                double wtot=sqrt(pow(glwlor/2,2)+pow(wgau,2))+glwlor/2;
                                                        //        glwlor=sqrt(pow(wgau,2)+pow(glwlor,2)-pow(atof(OKBottomDlg->Edit16->Text.c_str()),2));
                                                         //        double glwlor1=sqrt(pow(wgau,2)+pow(glwlor,2)-pow(atof(OKBottomDlg->Edit16->Text.c_str()),2));
                                                               double winst= atof(OKBottomDlg->Edit16->Text.c_str())/5000.*(Form9->Query3->FieldByName("asswavelen")->AsFloat);
                                                                glwlor=wtot-pow(winst,2)/wtot;
                                                                break;
                                                                }
                                                        else
                                                                {
                                                                Form9->Query3->Next();
                                                                }
                                                        }
   
                                                jjj++;
                                                Form20->StringGrid1->Cells[1][jjj]=lab;
                                                Form20->StringGrid1->Cells[2][jjj]=wa;
                                                char lor[20];
                                                sprintf(lor,"%1.3f",glwlor);
                                                Form20->StringGrid1->Cells[3][jjj]=lor;
                                                double strk=pow(10.,rtbis(test, nmin, nmax, xacc));
                                                double strk1=glwlor/2./glww*1e16;
                                                char stark[20];
                                                sprintf(stark,"%1.2E",strk);
                                                Form20->StringGrid1->Cells[4][jjj]=stark;
                                                break;
                                                }
                                        Form20->StringGrid1->RowCount=max(jjj+2,2);
                                        Form6->Query1->Next();
                                        }
                                }
                        Form20->Table1->Next();
                        }
                }
  // Fine calcolo Stark
        }
 }

//---------------------------------------------------------

  void report(AnsiString reportnam, AnsiString filenam, AnsiString templatenam)
{

     FILE *out;

   out = fopen(reportnam.c_str(), "a");
 //  fprintf(out,"Filename: %s\n",filenam);
  // fprintf(out,"Template: %s\n",templatenam);

   Form6->Table1->First();
  char lab [10];
 // fprintf(out,"\n[Specie] [Wavel.] [Fit Wavel.] [Int.] [Err.]   [Wg]  [Wl]\n");
// fprintf(out,"\n[Specie] [Wavel.] [Int.] \n");

  for (int i=0; i< Form6->Table1->RecordCount;i++)
  {

        int ioniz=Form6->Table1->FieldByName("ion")->AsInteger;

        Form6->Edit1->Text=Form6->Table1->FieldByName("specie")->AsString;

  switch(ioniz)
  {
  case 0:
  sprintf(lab,"-",Form6->Edit1->Text.c_str());
  break;
  case 1:
   sprintf(lab,"%sI",Form6->Edit1->Text.c_str());
   break;
  case 2:
   sprintf(lab,"%sII",Form6->Edit1->Text.c_str());
  break;
  }

 // fprintf(out,"%9s %6s %9s %9s %9s %9s %6s %6s\n",Form6->Table1->FieldByName("wavelen")->AsString,lab,Form6->Table1->FieldByName("asswavelen")->AsString,Form6->Table1->FieldByName("fitwavelen")->AsString,Form6->Table1->FieldByName("inte")->AsString,Form6->Table1->FieldByName("Error-inte")->AsString,Form6->Table1->FieldByName("wg")->AsString, Form6->Table1->FieldByName("wl")->AsString);
fprintf(out,"%9s %6s %9s \n",lab, Form6->Table1->FieldByName("asswavelen")->AsString,Form6->Table1->FieldByName("inte")->AsString);

           Form6->Table1->Next();
 }

 /* Inizio Parte nuova

 fprintf(out,"\n[Ek]  [I]  [ln(I/gkAki)]  [gk]  [Aki]  [Eff.]  [Specie] \n");
char sqls[300];
 sprintf(sqls,"SELECT DISTINCT SPECIE,ION FROM %s WHERE aki != 0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",ExtractFileName(Form6->Table1->TableName));
 Form9->Query1->Active=false;
Form9->Query1->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
 Form9->Query1->Active=true;
Form9->Query1->SQL->Clear();
Form9->Query1->SQL->Add(sqls);
Form9->Query1->Open();
Form9->Query1->First();
Form9->Query2->Active=false;
Form9->Query2->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query2->Active=true;

 sprintf(sqls,"SELECT DISTINCT SPECIE FROM %s WHERE aki != 0.0 AND inte > 0.0 AND aki !=-1.0 AND ion > 0 ORDER BY specie",ExtractFileName(Form6->Table1->TableName));
Form9->Query2->SQL->Clear();
Form9->Query2->SQL->Add(sqls);
Form9->Query2->Open();
Form9->Query2->First();

char sname[32];
for (int i=0; i < Form9->Query1->RecordCount; i++)
{



  Form9->Edit3->Text=Form9->Query1->FieldByName("specie")->AsString;
 Form9->Edit4->Text=Form9->Query1->FieldByName("ion")->AsString;

 int ioniz=Form9->Query1->FieldByName("ion")->AsInteger;
  switch(ioniz)
  {
  case 1:
   sprintf(sname,"%sI",Trim(Form9->Edit3->Text));
   break;
  case 2:
   sprintf(sname,"%sII",Trim(Form9->Edit3->Text));
  break;
  }


Form9->Query3->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query3->Active=true;
Form9->Query6->Active=false;
Form9->Query6->DatabaseName=ExtractFilePath(Form6->Table1->TableName);
Form9->Query6->Active=true;


 sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki != 0.0 AND aki !=-1.0 AND inte > 0.0",ExtractFileName(Form6->Table1->TableName),Form9->Edit3->Text,Form9->Edit4->Text);
Form9->Query3->SQL->Clear();
Form9->Query3->SQL->Add(sqls);
Form9->Query3->Open();

Form9->Query3->First();
     Form9->StringGrid1->Cells[2][i+1]=Form9->Query3->RecordCount;
for (int j=0; j < Form9->Query3->RecordCount; j++)
{
 float wave=Form9->Query3->FieldValues["wavelen"];
  float inte=Form9->Query3->FieldValues["inte"];
   float erro=Form9->Query3->FieldValues["error-inte"];
   float aki= Form9->Query3->FieldValues["aki"];
    int gk= Form9->Query3->FieldValues["gk"];
     float Ek= Form9->Query3->FieldValues["Ek"]*1.23985e-4;
     float yyy;


if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton2->Checked==true)
{
for (int k=0; k < Form10->Series1->Count(); k++)
{
 if (wave < Form10->Series1->XValues->Value[k])
 {
yyy=Form10->Series1->YValues->Value[k]+
(Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
(Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
(wave-Form10->Series1->XValues->Value[k]);
 goto aaa;
 }
 }
 }
 else
 {
 yyy=1.0;
 }
aaa:
 inte/=yyy;
 erro/=yyy;



float yy=log(inte/fabs(aki*gk));

fprintf(out,"%1.3f %1.3f %1.3f %3i %1.3f %1.3f %4s \n",Ek,inte,yy,gk,aki,yyy,sname);



 Form9->Query3->Next();
  }
 Form9->Query1->Next();
 }
  Form9->Query1->First();

// Fine parte nuova

      fprintf(out,"\n[Specie] [Lines] [Temp] [q] [Z(T)]\n");
      int i=0;

while (Form9->StringGrid1->Cells[1][i+1] != "")
{
 fprintf(out,"%6s %6s %6s %6s %8s\n",Form9->StringGrid1->Cells[1][i+1].c_str(),Form9->StringGrid1->Cells[2][i+1].c_str(),
 Form9->StringGrid1->Cells[3][i+1].c_str(),Form9->StringGrid1->Cells[4][i+1].c_str(),Form9->StringGrid1->Cells[5][i+1].c_str());
i++;
}


fprintf(out,"\n[Element]   [NConc]  [MConc.]   [Ne]   [I/(I+II)]\n");
i=0;
while (Form9->StringGrid2->Cells[1][i+1] != "")
{
 fprintf(out,"%6s %6s %6s %6s %6s\n",Form9->StringGrid2->Cells[1][i+1].c_str(),Form9->StringGrid2->Cells[2][i+1].c_str(),
 Form9->StringGrid2->Cells[3][i+1].c_str(),Form9->StringGrid2->Cells[4][i+1].c_str(),Form9->StringGrid2->Cells[5][i+1].c_str());
i++;
}
if (OKBottomDlg->CheckBox2->Checked)
 fprintf(out,"\nGlobal Correction: %s\n",OKBottomDlg->Edit10->Text.c_str());
else
  fprintf(out,"\nGlobal Correction: NO\n");

  if (OKBottomDlg->CheckBox1->Checked)
 fprintf(out,"Single File Correction: %s\n",OKBottomDlg->Edit11->Text.c_str());
else
  fprintf(out,"Single File Correction: NO\n");

    if (OKBottomDlg->RadioButton1->Checked)
 fprintf(out,"Correction before integral calculation\n");
else
  fprintf(out,"Correction after integral calculation\n");

switch (Form9->RadioGroup1->ItemIndex)
{
case 0:
 fprintf(out,"\nTemperature Free\n");
break;
case 1:
  fprintf(out,"\nTemperature Smart Average\n");
break;
case 2:
fprintf(out,"\nTemperature Locked at %s\n",Form9->Edit1->Text.c_str());
break;
}
switch (Form9->RadioGroup2->ItemIndex)
{
case 0:
 fprintf(out,"Ne Free\n");
break;
case 1:
  fprintf(out,"Ne Smart Average\n");
break;
case 2:
fprintf(out,"Ne Locked at %s\n",Form9->Edit2->Text.c_str());
break;
}
    fprintf(out,"Aver. Temp: %s\n",Form9->Edit7->Text.c_str());
     fprintf(out,"Aver. Ne: %s\n",Form9->Edit8->Text.c_str());

    fprintf(out,"\nReport completed on %s at %s\n",DateToStr(Date()),TimeToStr(Time()));
 */
  fclose(out);
  }
//---------------------------------------------------------------------------
void __fastcall TSDIAppForm::FormCreate(TObject *Sender)
{
Show();
Image1->Repaint();
Repaint();
Edit8->Text=ExtractFilePath(Application->ExeName)+"\Templates\\template.db";
}
//---------------------------------------------------------------------------





void __fastcall TSDIAppForm::GoTo1Click(TObject *Sender)
{
Form19->Show();
}
//---------------------------------------------------------------------------



void __fastcall TSDIAppForm::ToolButton6Click(TObject *Sender)
{
  void emergency(AnsiString nome);
Series4->Clear();
Series5->Clear();
emergency(Edit8->Text.c_str());
 Chart1->BottomAxis->Automatic=true;
  Chart1->LeftAxis->Automatic=true;
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ShowTempl1Click(TObject *Sender)
{
Form6->Show();
}
//---------------------------------------------------------------------------
void fit(float x[], float y[], int ndata, float sig[], int mwt, float *a, float *b, float *siga, float *sigb, float *chi2, float *q)
{
int i;
float wt,t,sxoss,sx=0.0,sy=0.0,st2=0.0,ss,sigdat;
*b=0.0;
if (mwt) {
ss=0.0;
for (i=0;i<=ndata;i++) {
wt=1.0/(sig[i]*sig[i]);
ss += wt;
sx += x[i]*wt;
sy += y[i]*wt;
}
} else {
for (i=0;i<=ndata;i++) {
sx += x[i];
sy += y[i];
}
ss=ndata;
}
sxoss=sx/ss;
if (mwt) {
for (i=0;i<=ndata;i++) {
t=(x[i]-sxoss)/sig[i];
st2 += t*t;
*b += t*y[i]/sig[i];
}
} else {
for (i=0;i<=ndata;i++) {
t=x[i]-sxoss;
st2 += t*t;
*b += t*y[i];
}
}
if (st2 == 0.0)
{
st2 = 0.01;
}
*b /= st2;
*a=(sy-sx*(*b))/ss;
*siga=sqrt((1.0+sx*sx/(ss*st2))/ss);
*sigb=sqrt(1.0/st2);
*chi2=0.0;
if (mwt == 0) {
for (i=0;i<=ndata;i++)
*chi2 += (y[i]-(*a)-(*b)*x[i])*(y[i]-(*a)-(*b)*x[i]);
*q=1.0;
sigdat=sqrt((*chi2)/(ndata-2));
*siga *= sigdat;
*sigb *= sigdat;
} else {
for (i=0;i<=ndata;i++)
*chi2 += ((y[i]-(*a)-(*b)*x[i])/sig[i])*((y[i]-(*a)-(*b)*x[i])/sig[i]);
*q=1.0;
}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Series4DblClick(TChartSeries *Sender,
      int ValueIndex, TMouseButton Button, TShiftState Shift, int X, int Y)
{
Form6->Table1->RecNo=ValueIndex+1;
}
//---------------------------------------------------------------------------

float rtbis(double (*func)(double), double x1, double x2, float xacc)
{
int j;
float dx,f,fmid,xmid,rtb;
f=(*func)(x1);
fmid=(*func)(x2);
if (f*fmid >= 0.0)
{
ShowMessage("Root must be bracketed for bisection in rtbis");
return 0.0;
}
rtb = f < 0.0 ? (dx=x2-x1,x1) : (dx=x1-x2,x2);
for (j=1;j<=100;j++) {
fmid=(*func)(xmid=rtb+(dx *= 0.5));
if (fmid <= 0.0) rtb=xmid;
if (fabs(dx) < xacc || fmid == 0.0) return rtb;
}
return 0.0;
}
//---------------------------------------------------------------------------

double test(double x)
{
double y;
 double xx=pow(10.,x-16);
  double r;
 double ex=1.0/6.0;
  r=(0.0899*pow(xx,ex))/sqrt(gltstar);
 double lar2=glww*xx;
   ex=0.25;
  double alfa2=glaa*pow(xx,ex);
// y=2.*(1.+1.75*alfa2*(1.0-0.75*r))*lar2-glwlor;
//   Form20->Chart1->Series[gljjj]->AddXY(x,y,' ',clTeeColor);
   return 2.*(1.+1.75*alfa2*(1.0-0.75*r))*lar2-glwlor;
}

//---------------------------------------------------------------------------
void plotgauss(float x, float a[], float *y, int na)
{
 int colo[34]={clWhite,clRed,clYellow,clGreen,clMaroon,clDkGray,clOlive,clPurple,clLtGray,clBlue,clNavy,clBlack,clFuchsia,clGray,clTeal,clSilver,clLime,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};

    int i,j,npeaks;

    double integra;

npeaks=(na-1)/3.0;

   for (j=1;j<na;j++)
   {
    a[j]=fabs(a[j]);
   }

  *y=a[0]+a[na]*x;

 SDIAppForm->Chart1->Series[6]->AddXY(x,*y,' ',colo[0]);

 for (j=0;j<npeaks;j++)
 {
*y=0.;
float arg=(x-a[2+3*j])/a[3+3*j];
float ex=exp(-arg*arg);
*y+=a[1+3*j]*ex;

//  Form14->Series1->Active=true;
//  Form14->Series1->YValues->Value[j]+=*y;
  SDIAppForm->Chart1->Series[7+j]->Active=true;
 SDIAppForm->Chart1->Series[7+j]->AddXY(x,*y,' ',colo[j+1]);
  }
 }

//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Undo1Click(TObject *Sender)
{
swap (Series1,Series2);
  Series2->Active=false;
  Series1->Active=true;

  if (Series5->Count() == Series4->Count())
  {
  swap(Series4,Series5);
  }
    Series5->Active=false;
  Series4->Active=true;        
}
//---------------------------------------------------------------------------


void __fastcall TSDIAppForm::InfoTempl1Click(TObject *Sender)
{
Form3->Show();
}
 //-------------------------------------------------------------------
 void retrofit(float jmin, float jmax, int j)
 {
 double integrale(float x, float w[]);
  int colo[34]={clWhite,clRed,clYellow,clGreen,clMaroon,clDkGray,clOlive,clPurple,clLtGray,clBlue,clNavy,clBlack,clFuchsia,clGray,clTeal,clSilver,clLime,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
  void gauss(float x, float a[], float *y, float dyda[], int na);
void voigt(float x, float a[], float *y, float dyda[], int na);
void plotvoigt(float x, float a[], float *y, int na);
void free_matrix(float **m, long nrl, long nrh, long ncl, long nch);
void free_vector(float *v, long nl, long nh);
void free_ivector(int *v, long nl, long nh);
void manfit();

 float *vector(long nl,long nh);
  int *ivector(long nl,long nh);

        Form14->Image2->Visible=false;
            Form14->Image1->Visible=false;
            Form14->Image3->Visible=false;

float y,*a,*origa,*chi;
float *dyda,delta0,delta,accu;
int k,group,na,oldj,upoints,*ia;

// Form6->Show();
 Form6->Table1->Refresh();
 Form6->Table1->First();

delta0=atof((OKBottomDlg->Edit8->Text).c_str());
accu=atof((OKBottomDlg->Edit12->Text).c_str());
SDIAppForm->Chart1->BottomAxis->Automatic=false;
   Form14->Edit2->Text="";
  float **covar,**alpha;
            float chisq,*xx,*z,*sg,oldchisq,ran;
             float alamda,maxax,minax,maxay,minay,firstin,lastin;
             int g;
      minay=0;
     SDIAppForm->Series1->Active=true;
     SDIAppForm->Series3->Active=true;
     SDIAppForm->Series4->Active=true;
// for (j=jmin;j<=jmax;j++)
// {
  group=1;
  oldj=j;
  delta= delta0*(SDIAppForm->Series4->XValues->Value[oldj])/5000.;
  minax=SDIAppForm->Series4->XValues->Value[oldj]-delta;
  maxax=SDIAppForm->Series4->XValues->Value[oldj]+delta;
 while (j>jmin && SDIAppForm->Series4->XValues->Value[j-1] > (minax-delta))
  {
  group++;
  j--;
  minax=SDIAppForm->Series4->XValues->Value[j]-delta;
  }

    SDIAppForm->Edit12->Text=j;
     SDIAppForm->Chart1->BottomAxis->SetMinMax(minax,maxax);

  SDIAppForm->Chart1->Refresh();

     minay=0;
      maxay=0;

for (int j=0;j<SDIAppForm->Chart1->SeriesCount();j++)
{
if (SDIAppForm->Chart1->Series[j]->FirstValueIndex > 0)
        {
  for (int pu=SDIAppForm->Chart1->Series[j]->FirstValueIndex;pu <= SDIAppForm->Chart1->Series[j]->LastValueIndex;pu++)
  {
  if (SDIAppForm->Chart1->Series[j]->YValues->Value[pu] > maxay) maxay= SDIAppForm->Chart1->Series[j]->YValues->Value[pu];
  }
        }
}

  SDIAppForm->Chart1->LeftAxis->Automatic=false;

  SDIAppForm->Chart1->LeftAxis->SetMinMax(minay,maxay*1.1);

 // SDIAppForm->Chart1->LeftAxis->Automatic=true;
    SDIAppForm->Chart1->Refresh();

 //  }

  //  SDIAppForm->Chart1->BottomAxis->Automatic=true;
  //  SDIAppForm->Chart1->LeftAxis->Automatic=true;

   }
 //------------------------------------------------------------------
      void emergency(AnsiString nome)
 {

 Form6->Table1->Active=false;
  Form6->Query1->Active=false;
  Form6->Table1->TableType=ttParadox;
  Form6->Table1->TableName=nome;
   Form6->Table1->Active=true;
     Form6->Query1->Active=true;
       float soglia=atof(OKBottomDlg->Edit17->Text.c_str());
  float pp=1.0;
   char sqls[300];
  sprintf(sqls,"select * from '%s' order by templint",nome);
   Form6->Query1->SQL->Clear();
 Form6->Query1->SQL->Add(sqls);
 Form6->Query1->Open();
 Form6->Query1->Last();
 float maxim=Form6->Query1->FieldValues["templint"];
sprintf(sqls,"SELECT * FROM '%s' ORDER BY ASSWAVELEN",Form6->Table1->TableName.c_str());
 Form6->Query1->SQL->Clear();
 Form6->Query1->SQL->Add(sqls);
 Form6->Query1->Open();
 Form6->Query1->First();
 Form6->Caption="Active Template:"+nome;
  SDIAppForm->Series4->Clear();
     float myp;
  if (SDIAppForm->Series1->MaxYValue()  != SDIAppForm->Series1->MinYValue() )
   {
    myp= SDIAppForm->Series1->MaxYValue();
   }
   else
   {
    myp=1.0;
   }


  char lab[300];
  Form6->Table1->First();
  SDIAppForm->Series4->XValues->Order = loNone;

  for (int i=0; i < Form6->Table1->RecordCount; i++)
  {
   Form6->Table1->Edit();
   Form6->Table1->FieldValues["wavelen"]=Form6->Table1->FieldByName("asswavelen")->AsFloat;
   Form6->Table1->FieldValues["fitwavelen"]=Form6->Table1->FieldByName("asswavelen")->AsFloat;
     Form6->Table1->Refresh();
  int ioniz=Form6->Table1->FieldByName("ion")->AsInteger;
    if (ioniz != 0)
    {
  switch(ioniz)
  {
  case 1:
  sprintf(lab,"%s I",Form6->Table1->FieldByName("specie")->AsString);
   break;
  case 2:
     sprintf(lab,"%s II",Form6->Table1->FieldByName("specie")->AsString);
  break;
  }
  if (Form6->Table1->FieldByName("Aki")->AsFloat > soglia)
  {
   SDIAppForm->Series4->AddXY(Form6->Table1->FieldValues["wavelen"],Form6->Table1->FieldValues["templint"],lab,clYellow);
   }
   else
   {
    SDIAppForm->Series4->AddXY(Form6->Table1->FieldValues["wavelen"],Form6->Table1->FieldValues["templint"],lab,COLORE);
   }
    }
     else
    {
   sprintf(lab,"%4.2f",Form6->Table1->FieldByName("wavelen")->AsFloat);
   SDIAppForm->Series4->AddXY(Form6->Table1->FieldValues["wavelen"],Form6->Table1->FieldValues["templint"],lab,clBlue);
   }
 Form6->Table1->Next();
  }
  SDIAppForm->Series4->XValues->Order = loAscending;
  Form6->Table1->First();
  SDIAppForm->Edit5->Text=1;
  Form6->DBNavigator1->Enabled=true;



// apertura correzioni

AnsiString fn = ChangeFileExt(nome,".cor");
 char ppp[300];


  FILE *in;


   if (FileExists(fn.c_str())==false){ShowMessage("Template information file doesn't exist. Select it manually in the Options window");
                                        Form3->Edit2->Text="";
                                        Form3->Edit3->Text="";
                                        Form3->Version->Text="";
                                        Form3->Edit5->Text="";
                                        Form3->Edit6->Text="";
                                        Form3->Memo1->Lines->Text="";
                                        }
   else
  {
    in = fopen(fn.c_str(),"rt");

    TMsgDlgButtons msbut;
        msbut.Clear();
         msbut << mbYes << mbCancel;

    fscanf(in,"Global Correction: %s", &ppp);
    if(strcmp(ppp,"NO")!=0)     {
                                if (FileExists(ppp)){OKBottomDlg->Edit10->Text=ppp;
                                                        Form3->Edit5->Text=ppp;
                                                        }
                                else    {

                                       if (MessageDlg("The Global Correction file " + StrPas(ppp) + " \n can't be found. Select it manually ?", mtWarning, msbut, 0)== 6)
                                                {

                                                SDIAppForm->OpenDialog2->FileName=ppp;
                                                SDIAppForm->OpenDialog2->InitialDir=ExtractFilePath(Application->ExeName);
                                                if (SDIAppForm->OpenDialog2->Execute()){
                                                              OKBottomDlg->Edit10->Text= SDIAppForm->OpenDialog2->FileName;
                                                              Form3->Edit5->Text=ppp;
                                                              }
                                                }



                                        }
                                }
    fscanf(in,"\nSingle File Correction: %s", &ppp);
    if(strcmp(ppp,"NO")!=0) {
                                if (FileExists(ppp))    {OKBottomDlg->Edit11->Text=ppp;
                                                        Form3->Edit6->Text=ppp;
                                                        }
                                else  {

                                       if (MessageDlg("The Single Correction file " + StrPas(ppp) + " \n can't be found. Select it manually ?", mtWarning, msbut, 0)== 6)
                                                {

                                                SDIAppForm->OpenDialog2->FileName=ppp;
                                                SDIAppForm->OpenDialog2->InitialDir=ExtractFilePath(Application->ExeName);
                                                if (SDIAppForm->OpenDialog2->Execute()){
                                                              OKBottomDlg->Edit11->Text= SDIAppForm->OpenDialog2->FileName;
                                                              Form3->Edit6->Text=ppp;
                                                              }
                                                }



                                        }
                             }

    fscanf(in,"\nCorrection %s integral calculation", &ppp);
    Form3->Label6->Caption=ppp;
    fscanf(in,"\nSpectrum Filename: %s", &ppp);
        if(strcmp(ppp,"none")!=0)Form3->Edit2->Text=ppp;
        else Form3->Edit2->Text="";
    fscanf(in,"\nUser: %s", &ppp);
        if(strcmp(ppp,"none")!=0)Form3->Edit1->Text=ppp;
        else Form3->Edit1->Text="";
    fscanf(in,"\nVersion: %s", &ppp);
    Form3->Version->Text=ppp;
    fscanf(in,"\nCreated Date: %s", &ppp);
    Form3->Edit3->Text=ppp;
    char notes[300]="";
    char buf[20]="";
    fscanf(in,"\nNotes:");
    do {strcat(notes,buf);
        strcat(notes," ");}
    while (fscanf(in,"%s", &buf)!=EOF);

    Form3->Memo1->Lines->Text=notes;


    fclose(in);
  }

  }
 //---------------------------------------------------------------------------
 void compfile(AnsiString nomefile)
 {
 int handle;

 int colo[34]={clRed,clGreen,clYellow,clOlive,clPurple,clDkGray,clFuchsia,clTeal,clSilver,clLime,clLtGray,clBlack,clBlue,clGray,clNavy,clWhite,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};


  int sc,lc,jfin;
  sc=SDIAppForm->Chart1->SeriesCount();

 for (int j=0;j<=Form13->StringGrid1->RowCount;j++)
  {
  if   (Form13->StringGrid1->Cells[1][j] =="")
  {
  jfin=j;
  break;
  }
  }

 SDIAppForm->Series2->Clear();


      TLineSeries *MySeries = new TLineSeries(SDIAppForm);
         MySeries->ParentChart=SDIAppForm->Chart1;
    MySeries->LinePen->Style=psSolid;
      MySeries->SeriesColor=colo[sc-6];


          MySeries->Active=true;
           MySeries->XValues->Order = loAscending;
           MySeries->Clear();
           AnsiString sd = "";
                sd.cat_sprintf("s%i", sc-5);

            MySeries->Name=sd;


   double wave;
   double lips;
   float yyy;
   FILE *stream;
 // SDIAppForm->Caption = "Opening File:" + nomefile;
  SDIAppForm->Edit9->Text = nomefile;
  handle = open((nomefile).c_str(),O_RDONLY);
  stream = fdopen(handle, "r");



  do
   {
   fscanf(stream,"%le %le", &wave, &lips);
    if ((OKBottomDlg->CheckBox7->Checked==true) & (wave < 1500))
    wave=wave*10;
   if ((wave <= atof(OKBottomDlg->Edit4->Text.c_str()))  & (wave >= atof(OKBottomDlg->Edit3->Text.c_str())))
  {
 MySeries->AddXY(wave+atof(OKBottomDlg->Edit23->Text.c_str()),lips,' ',colo[sc-6]);
  }
 else
 {
 }
 }
   while (!eof(handle));
   close(handle);

    float ofs;
  if  (OKBottomDlg->CheckBox8->Checked==true)
  {
  ofs=MySeries->YValues->MinValue;
   for (int i=0; i < MySeries->Count(); i++)
  {
   MySeries->YValues->Value[i]-=ofs;
   }
  }


if (OKBottomDlg->CheckBox2->Checked==true && OKBottomDlg->RadioButton1->Checked==true)
 {

 for (int i=0; i < MySeries->Count(); i++)
 {
 wave=MySeries->XValues->Value[i];

  for (int k=1; k < Form10->Series1->Count(); k++)
{
 if (wave < Form10->Series1->XValues->Value[k])
{
yyy=Form10->Series1->YValues->Value[k]+
(Form10->Series1->YValues->Value[k-1]-Form10->Series1->YValues->Value[k])/
(Form10->Series1->XValues->Value[k-1]-Form10->Series1->XValues->Value[k])*
(wave-Form10->Series1->XValues->Value[k]);
MySeries->YValues->Value[i]/=yyy;
break;
 }
}
}

MySeries->Active=true;

MySeries->XValues->Order = loAscending;
}

   SDIAppForm->Edit5->Text=1;
  }
//----------------------------------------------------------
void __fastcall TSDIAppForm::Compare1Click(TObject *Sender)
{
void compfile(AnsiString nomefile);

  OpenDialog->FileName = "";
     OpenDialog->Filter = "Mechelle Files (*.mch)|*.MCH|All Files (*.*)|*.*";

     AnsiString fp;
     OpenDialog->InitialDir=SDIAppForm->Edit14->Text;

    if (OpenDialog->Execute())
  {
  SaveDialog->FileName = OpenDialog->FileName;

   for (int y=1;y<Form13->StringGrid1->RowCount;y++)
     {
     if (Form13->StringGrid1->Cells[1][y]=="")
    {
    Form13->StringGrid1->Cells[1][y]=OpenDialog->FileName;
    Form13->StringGrid1->Refresh();
    break;
    }
      }

  compfile(OpenDialog->FileName);
      fp=(ExtractFilePath(OpenDialog->FileName));
       SDIAppForm->Edit14->Text=fp;
  }
}
//---------------------------------------------------------------------------
 void exc()
 {
 int colo[34]={clRed,clGreen,clYellow,clOlive,clPurple,clDkGray,clFuchsia,clTeal,clSilver,clLime,clLtGray,clBlack,clBlue,clGray,clNavy,clWhite,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
     if (Form13->Edit1->Text == "") return;
     int rw=Form13->StringGrid1->Row;
     AnsiString nm;
      AnsiString cp="";
         int ru;

  if (rw==0)
   {
 ShowMessage ("Spectrum is already selected as main");
 return;
    }
       cp.cat_sprintf("s%i",rw);

   for (int u=0; u < SDIAppForm->Chart1->SeriesCount();u++)
   {
   nm=SDIAppForm->Chart1->Series[u]->Name;
    if (nm == cp)
    {
    ru=u;
    break;
    }
 }

 // ru--;

 // if (rw==1) ru=;

SDIAppForm->Caption = "Current File:" + ExtractFileName(Form13->Edit1->Text);
  AnsiString tp;
  tp=Form13->StringGrid1->Cells[1][Form13->StringGrid1->Row];
 Form13->StringGrid1->Cells[1][Form13->StringGrid1->Row]=Form13->StringGrid1->Cells[1][0];
   Form13->StringGrid1->Cells[1][0]=tp;
      tp=Form13->StringGrid1->Cells[0][Form13->StringGrid1->Row];
 Form13->StringGrid1->Cells[0][Form13->StringGrid1->Row]=Form13->StringGrid1->Cells[0][0];
   Form13->StringGrid1->Cells[0][0]=tp;

         Form13->StringGrid1->Refresh();
    Form13->Edit1->Text= Form13->StringGrid1->Cells[Form13->StringGrid1->Col][Form13->StringGrid1->Row];
    
 SDIAppForm->Series2->Clear();
     SDIAppForm->Series1->Active=false;

for (int q=0; q < SDIAppForm->Series1->Count();q++)
{
   SDIAppForm->Series2->AddXY(SDIAppForm->Chart1->Series[0]->XValues->Value[q],SDIAppForm->Chart1->Series[0]->YValues->Value[q],' ',clWhite);
 }

     SDIAppForm->Chart1->Series[0]->Clear();
      SDIAppForm->Chart1->Series[ru]->Active=false;

for (int q=0; q < SDIAppForm->Chart1->Series[ru]->Count();q++)
{
   SDIAppForm->Chart1->Series[0]->AddXY(SDIAppForm->Chart1->Series[ru]->XValues->Value[q],SDIAppForm->Chart1->Series[ru]->YValues->Value[q],' ',clBlack);
 }

   SDIAppForm->Chart1->Series[ru]->Clear();

 for (int q=0; q < SDIAppForm->Series2->Count();q++)
{
   SDIAppForm->Chart1->Series[ru]->AddXY(SDIAppForm->Series2->XValues->Value[q],SDIAppForm->Series2->YValues->Value[q],' ',colo[rw-1]);

 }

   SDIAppForm->Series2->Active=false;
 SDIAppForm->Chart1->Series[0]->Active=true;
 SDIAppForm->Chart1->Series[ru]->Active=true;
SDIAppForm->Chart1->Refresh();
return;
  }
//-----------------------------------------------------------------------------
void __fastcall TSDIAppForm::ShowSpectraList1Click(TObject *Sender)
{
Form13->StringGrid1->ColWidths[0]=12;
Form13->StringGrid1->ColWidths[1]=400;
Form13->Edit1->Text="";
Form13->Show();
}
//---------------------------------------------------------------------------






void __fastcall TSDIAppForm::Timer1Timer(TObject *Sender)
{
SDIAppForm->Image1->Visible=false;
}
//---------------------------------------------------------------------------

  void manfit()
  {
 double integrale(float x, float w[]);
int colo[34]={clWhite,clRed,clYellow,clGreen,clMaroon,clDkGray,clOlive,clPurple,clLtGray,clBlue,clNavy,clBlack,clFuchsia,clGray,clTeal,clSilver,clLime,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
void gauss(float x, float a[], float *y, float dyda[], int na);
void voigt(float x, float a[], float *y, float dyda[], int na);
void plotvoigt(float x, float a[], float *y, int na);
void free_matrix(float **m, long nrl, long nrh, long ncl, long nch);
void free_vector(float *v, long nl, long nh);
void free_ivector(int *v, long nl, long nh);

 float *vector(long nl,long nh);
  int *ivector(long nl,long nh);

float y,*a,*origa,*chi;
float *dyda,delta,accu;
int j,k,upoints,*ia;

  float **covar,**alpha;
  float chisq,*xx,*z,*sg,oldchisq,ran;
  float alamda,maxax,minax;
  int g;


  accu=atof((OKBottomDlg->Edit12->Text).c_str());

     SDIAppForm->Series1->Active=true;
     SDIAppForm->Series3->Active=true;
     SDIAppForm->Series4->Active=true;

 SDIAppForm->Chart1->BottomAxis->Automatic=false;

 int group = (SDIAppForm->Series4->LastValueIndex - SDIAppForm->Series4->FirstValueIndex) +1;

   if (group > 10)
   {
   Form14->Show();
   Form14->Edit2->Text="Too many lines for fitting (> 10)";

     return;
   }

  int na=group*4+1;

         a=vector(0,na);
          origa=vector(0,na);
          ia=ivector(0,na);
           chi=vector(0,na);
            dyda=vector(0,na);

   a[0]=(SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->LastValueIndex]*SDIAppForm->Series1->YValues->Value[SDIAppForm->Series1->FirstValueIndex]-SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->FirstValueIndex]*SDIAppForm->Series1->YValues->Value[SDIAppForm->Series1->LastValueIndex])/(SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->LastValueIndex]-SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->FirstValueIndex]);
     a[na]=(SDIAppForm->Series1->YValues->Value[SDIAppForm->Series1->LastValueIndex]-SDIAppForm->Series1->YValues->Value[SDIAppForm->Series1->FirstValueIndex])/(SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->LastValueIndex]-SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->FirstValueIndex]);

      ia[0]=1;
       ia[na]=1;
        origa[0]=a[0];
         origa[na]=a[na];

  float yy5;

  for (k=0;k<group;k++)
  {
   float xx=SDIAppForm->Series4->XValues->Value[SDIAppForm->Series4->FirstValueIndex+k];
  for (int w=SDIAppForm->Series1->FirstValueIndex;w<SDIAppForm->Series1->LastValueIndex;w++)
{
 if (SDIAppForm->Series1->XValues->Value[w] > xx)
 {
 yy5=SDIAppForm->Series1->YValues->Value[w]+
(SDIAppForm->Series1->YValues->Value[w-1]-SDIAppForm->Series1->YValues->Value[w])/
(SDIAppForm->Series1->XValues->Value[w-1]-SDIAppForm->Series1->XValues->Value[w])*
(xx-SDIAppForm->Series1->XValues->Value[w]);
 break;
 }
 }


      a[2+k*4]= SDIAppForm->Series4->XValues->Value[SDIAppForm->Series4->FirstValueIndex+k];
         origa[2+k*4]=a[2+k*4];
         a[3+k*4]= atof(OKBottomDlg->Edit14->Text.c_str())/2.;
          origa[3+k*4]=a[3+k*4];
         a[4+k*4]= atof(OKBottomDlg->Edit15->Text.c_str())/2.;
          origa[4+k*4]=a[4+k*4];
         origa[1+k*4]=a[1+k*4];
          ia[1+k*4]=1;

 //      a[1+k*4]= 2.*(SDIAppForm->Series4->YValues->Value[SDIAppForm->Series4->FirstValueIndex+k]-a[0]-a[2+k*4]*a[na])*(a[3+k*4]+a[4+k*4])*6.28;
  //     a[1+k*4]= 2.*(yy5-a[0]-a[2+k*4]*a[na])*(a[3+k*4]+a[4+k*4])*6.28;

          a[1+k*4]=(yy5-a[0]-a[2+k*4]*a[na])*(a[3+k*4]+a[4+k*4])*6.28;


          switch (OKBottomDlg->CheckBox4->Checked)
          {
          case true:
           ia[2+k*4]=0;
           break;
          case false:
          ia[2+k*4]=1;
          break;
          }
              switch (OKBottomDlg->CheckBox5->Checked)
          {
          case true:
           ia[3+k*4]=0;
           break;
          case false:
          ia[3+k*4]=1;
          break;
          }
              switch (OKBottomDlg->CheckBox6->Checked)
          {
          case true:
           ia[4+k*4]=0;
           break;
          case false:
          ia[4+k*4]=1;
          break;
          }
  }


  int u;

  int  firstin=SDIAppForm->Series1->FirstValueIndex;
    int  lastin=SDIAppForm->Series1->LastValueIndex;
      int  firstlin=SDIAppForm->Series4->FirstValueIndex;
    int  lastlin=SDIAppForm->Series4->LastValueIndex;

   upoints= (lastin-firstin);
   xx=vector(0,upoints);
   z=vector(0,upoints);
   sg=vector(0,upoints);


  if ((lastin-firstin)>5000)
  {
   Form14->Show();
   Form14->Edit2->Text="Spectral range too wide";
     return;
   }
   for (u=0,g=firstin;g<lastin;g++,u++)
   {
   xx[u]=SDIAppForm->Series1->XValues->Value[g];
   z[u]=SDIAppForm->Series1->YValues->Value[g];
       if (z[u] <= 0.0)
     sg[u]=1.0;
     else
   sg[u]=max(sqrt(z[u]),1.0);
   }

  /*
     SDIAppForm->Series3->Clear();
     for (g=0;g<upoints;g++)
        {
       voigt(xx[g],a,&y,dyda,na);
       SDIAppForm->Series3->AddXY(xx[g],y,' ',clBlue);
        }
        ShowMessage("Condizioni Iniziali");
 */

        alpha=matrix(0,na,0,na);
         covar=matrix(0,na,0,na);
                alamda=-1.0;
                int stp;
               chisq=1.0E18;
               int maxcounts;
                maxcounts=atof(OKBottomDlg->Edit22->Text.c_str());
                int count;
            int maxcount;
           maxcount=atof(OKBottomDlg->Edit22->Text.c_str());
               oldchisq=2.0E18;
               chisq=1.0E18;

 int sc=SDIAppForm->Chart1->SeriesCount();
    SDIAppForm->Edit13->Text=sc;


  for (g=0; g < group+1;g++)
  {
  TLineSeries *MySeries = new TLineSeries(SDIAppForm);
  MySeries->LinePen->Style=psDot;
   MySeries->ParentChart=SDIAppForm->Chart1;
   SDIAppForm->Chart1->Series[sc+g]->XValues->Order=loAscending;
  }

     Form14->Image2->Visible=false;
      Form14->Image1->Visible=false;
       Form14->Image3->Visible=false;
  // DA CAPO

 Again:
        SDIAppForm->Edit3->Text="0";
        count=0;
        stp=0;

 // Ciclo fit

  while( count < maxcount)

   {

   
     count++;
          oldchisq=chisq;

         mrqmin(xx,z,sg,upoints,a,ia,na,covar,alpha,&chisq,voigt,&alamda);

 // Inizio if
       if (alamda > 1e20)
       {
       Form14->Edit2->Text="Limits reached. Fit stopped.";
       Form14->Image1->Visible=true;
        Form14->Image2->Visible=false;
         Form14->Image3->Visible=false;

    //   ShowMessage("The fit is becoming unstable. If you choose to abort, the parameters will be reset at initial values");

   //  Form16->FormStyle=fsStayOnTop;

 // Form14->ModalResult=0;
    Form14->Close();
     Form14->ShowModal();
        int re;
       re = atoi((SDIAppForm->Edit7->Text).c_str());

 //  int re=0;
          switch (re)
          {
          case 0:
          Form14->Show();
          Form14->Image2->Visible=false;
           Form14->Image1->Visible=true;
         Form14->Image3->Visible=false;

          goto ex;
          case 1:
          goto Again;
 // Inizio reset
          case -1:
          SDIAppForm->Edit7->Text=0;
          Form14->Show();
          Form14->Image2->Visible=true;
           Form14->Image1->Visible=false;
         Form14->Image3->Visible=false;
          Form14->Edit2->Text="Fit aborted.";
          SDIAppForm->Series3->Clear();
           int g=-1;
          for (int gg=firstlin; gg <=lastlin;gg++)
           {
           g++;
            Form6->Table1->RecNo=gg+1;
       Form6->Table1->Edit();
             Form6->Table1->FieldValues["inte"]=0;
            }
              Form6->Table1->Post();
    if ( SDIAppForm->Chart1->SeriesCount() > sc)
   {
   int sma=SDIAppForm->Chart1->SeriesCount();
   for (int su=sma-1; su > sc-1 ;su--)
   {
   SDIAppForm->Chart1->Series[su]->Free();
   }
   }



   a[0]=origa[0];
    a[na]=origa[na];

         for (k=0;k<group;k++)
  {
   a[1+k*4]=origa[1+k*4];
    a[2+k*4]=origa[2+k*4];
     a[3+k*4]=origa[3+k*4];
      a[4+k*4]=origa[4+k*4];
        SDIAppForm->Series4->XValues->Value[SDIAppForm->Series4->FirstValueIndex+k]=a[2+k*4];
           char wa[20];
           sprintf(wa,"%4.2f",a[2+k*4]);
  if (atof(SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k].c_str()) !=0.0)
               SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k]=wa;
               count=maxcount;
 // fine reset
       }
  //fine case
       return;
       }
      }
  //fine if

           SDIAppForm->Series3->Clear();

           ran=atof(OKBottomDlg->Edit9->Text.c_str());

            for (k=0;k<group;k++)
  {
            SDIAppForm->Series4->XValues->Value[SDIAppForm->Series4->FirstValueIndex+k]=a[2+k*4];
           char wa[20];
           sprintf(wa,"%4.2f",a[2+k*4]);
            if (atof(SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k].c_str()) !=0.0)
               SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k]=wa;
 // Inizio if

            if ((a[2+k*4]< SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->FirstValueIndex]) || (a[2+k*4] > SDIAppForm->Series1->XValues->Value[SDIAppForm->Series1->LastValueIndex]))
            {
            Form14->Edit2->Text="Parameters unstable. Fit aborted.";
            Form14->Image2->Visible=true;
            Form14->Image1->Visible=false;
            Form14->Image3->Visible=false;

          switch (-1)
          {
          case 0:
          goto ex;
          case 1:
          goto Again;
  // Inizio reset
          case -1:

          int g=-1;
          for (int gg=firstlin; gg <=lastlin;gg++)
           {
           g++;
           Form6->Table1->RecNo=gg+1;
              Form6->Table1->Edit();
             Form6->Table1->FieldValues["inte"]=0;
            }
              Form6->Table1->Post();

          SDIAppForm->Series3->Clear();

             if ( SDIAppForm->Chart1->SeriesCount() > sc)
   {
   int sma=SDIAppForm->Chart1->SeriesCount();
   for (int su=sma-1; su > sc-1 ;su--)
   {
   SDIAppForm->Chart1->Series[su]->Free();
   }
   }


  /*
             if ( SDIAppForm->Chart1->SeriesCount() > 6)
   {
   int sma=SDIAppForm->Chart1->SeriesCount();
   for (int su=6; su < sma ;su++)
   {
   SDIAppForm->Chart1->Series[6]->Free();
   }
   }
 */
    a[0]=origa[0];
    a[na]=origa[na];

         for (k=0;k<group;k++)
  {
   a[1+k*4]=origa[1+k*4];
    a[2+k*4]=origa[2+k*4];
     a[3+k*4]=origa[3+k*4];
      a[4+k*4]=origa[4+k*4];
        SDIAppForm->Series4->XValues->Value[SDIAppForm->Series4->FirstValueIndex+k]=a[2+k*4];
           char wa[20];
           sprintf(wa,"%4.2f",a[2+k*4]);
  if (atof(SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k].c_str()) !=0.0)
               SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k]=wa;
               count=maxcount;
  // fine reset
       }
  //  Fine Case
       return;
       }

      }

   }
 // fine if

    if (OKBottomDlg->CheckBox3->Checked==True)       // Show Progress
 {
    Form14->Show();

    Form14->StringGrid1->RowCount=4*group+3;

         char kpt[20];
  for (g=0; g < group;g++)
  {
    Form14->StringGrid1->Cells[0][1]="Const.";
   Form14->StringGrid1->Cells[0][2]="Slope";
   Form14->StringGrid1->Cells[0][3+4*g]="Inten.";
    Form14->StringGrid1->Cells[0][4+4*g]="Wav.";
       Form14->StringGrid1->Cells[0][5+4*g]="wg";
    Form14->StringGrid1->Cells[0][6+4*g]="wl";

       sprintf(kpt,"%4.4f",a[0]);
 Form14->StringGrid1->Cells[1][1]=kpt;
        sprintf(kpt,"%4.4f",a[4*group+1]);
  Form14->StringGrid1->Cells[1][2]=kpt;
          sprintf(kpt,"%6.4f",a[1+4*g]);
   Form14->StringGrid1->Cells[1][3+4*g]=kpt;
   sprintf(kpt,"%4.2f",a[2+4*g]);
    Form14->StringGrid1->Cells[1][4+4*g]=kpt;
    sprintf(kpt,"%1.4f",2*a[3+4*g]);
       Form14->StringGrid1->Cells[1][5+4*g]=kpt;
       sprintf(kpt,"%6.4f",2*a[4*g+4]);
    Form14->StringGrid1->Cells[1][6+4*g]=kpt;

     sprintf(kpt,"%6.4f",chisq/upoints);
    Form14->Edit1->Text=kpt;
     Form14->StringGrid1->Refresh();
     Form14->Refresh();
   }


     Form14->Series1->Clear();
        Form14->Series2->Clear();
        for (g=0;g<group;g++)
        {
      Form14->Series1->AddXY(g,0,' ',colo[g+1]);
         Form14->Series2->AddXY(g,0,' ',colo[g+1]);
        }

         int npeaks=(na-1)/4.0;

       for (j=0;j<npeaks+1;j++)
       {
       SDIAppForm->Chart1->Series[sc+j]->Clear();
        }

       for (g=0;g<upoints;g++)
        {
       voigt(xx[g],a,&y,dyda,na);
       SDIAppForm->Series3->AddXY(xx[g],y,' ',clBlue);
       plotvoigt(xx[g],a,&y,na);
        }

 //      float dx=(xx[upoints-1]-xx[0])/upoints;

    double result;

  float *w=vector(0,3);
  float dw0=atof((OKBottomDlg->Edit8->Text).c_str());
      for (g=0;g<group;g++)
        {
         w[0]= a[1+4*g];
         w[1]= a[2+4*g];
         w[2]= a[3+4*g];
         w[3]= a[4+4*g];

         float dw=dw0*w[1]/5000.;
    float xmin=w[1]-3*dw;
        float xmax=w[1]+3*dw;
      result=2*(integrale(xmax, w)- integrale(xmin, w));


  //      result=integrale(xx[upoints-1], w)- integrale(xx[0], w);

  // result=a[4+4*g]*a[1+4*g]*sqrt(3.14151)*sqrt(log(2.))/a[3+4*g];

        Form14->Series1->YValues->Value[g]=result;
        double glwlor=2*a[4+4*g];
        double wgau=2*a[3+4*g];
        double wtot=sqrt(pow(glwlor/2,2)+pow(wgau,2))+glwlor/2;
        double inst=atof(OKBottomDlg->Edit16->Text.c_str())/5000.*a[2+4*g];
        glwlor=wtot-pow(inst,2)/wtot;
        Form14->Series2->YValues->Value[g]=glwlor;
        }
       free_vector(w,0,3);
      Form14->Chart1->Refresh();
        SDIAppForm->Chart1->Refresh();


     }
    Form14->ProgressBar1->Position=100*count/maxcount;
        }
  // fine counts


    //    Form14->FormStyle=fsStayOnTop;

    Form14->Edit2->Text="More fitting possible.";
          Form14->Image2->Visible=false;
           Form14->Image1->Visible=false;
         Form14->Image3->Visible=true;

    Form14->Close();
     Form14->ShowModal();

      int re1;
      re1 = atoi((SDIAppForm->Edit7->Text).c_str());

          switch (re1)
          {
          case 0:
          Form14->Show();
          Form14->Image1->Visible=true;
          Form14->Image3->Visible=false;
          goto ex;
          case 1:
           SDIAppForm->Edit7->Text=0;
          Form14->Edit2->Text="Continuing fitting....";
          Form14->Image3->Visible=false;
          goto Again;
 // Inizio reset
          case -1:
          SDIAppForm->Edit7->Text=0;
          Form14->Show();
          Form14->Image2->Visible=true;
           Form14->Image1->Visible=false;
         Form14->Image3->Visible=false;
          Form14->Edit2->Text="Fit aborted.";
          SDIAppForm->Series3->Clear();
           int g=-1;
          for (int gg=firstlin; gg <=lastlin;gg++)
           {
           g++;
            Form6->Table1->RecNo=gg+1;
       Form6->Table1->Edit();
             Form6->Table1->FieldValues["inte"]=0;
            }
              Form6->Table1->Post();
    if ( SDIAppForm->Chart1->SeriesCount() > sc)
   {
   int sma=SDIAppForm->Chart1->SeriesCount();
   for (int su=sma-1; su > sc-1 ;su--)
   {
   SDIAppForm->Chart1->Series[su]->Free();
   }
   }



   a[0]=origa[0];
    a[na]=origa[na];

         for (k=0;k<group;k++)
  {
   a[1+k*4]=origa[1+k*4];
    a[2+k*4]=origa[2+k*4];
     a[3+k*4]=origa[3+k*4];
      a[4+k*4]=origa[4+k*4];
        SDIAppForm->Series4->XValues->Value[SDIAppForm->Series4->FirstValueIndex+k]=a[2+k*4];
           char wa[20];
           sprintf(wa,"%4.2f",a[2+k*4]);
  if (atof(SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k].c_str()) !=0.0)
               SDIAppForm->Series4->XLabel[SDIAppForm->Series4->FirstValueIndex+k]=wa;
               count=maxcount;
   //fine reset
       }
       // Fine case
          return;
          }


 // Uscita OK

  ex:
     alamda=0;
      mrqmin(xx,z,sg,upoints,a,ia,na,covar,alpha,&chisq,voigt,&alamda);

         char kpt[20];
  for (g=0; g < group;g++)
  {
    Form14->StringGrid1->Cells[0][1]="Const.";
   Form14->StringGrid1->Cells[0][2]="Slope";
   Form14->StringGrid1->Cells[0][3+4*g]="Inten.";
    Form14->StringGrid1->Cells[0][4+4*g]="Wav.";
       Form14->StringGrid1->Cells[0][5+4*g]="wg";
    Form14->StringGrid1->Cells[0][6+4*g]="wl";

       sprintf(kpt,"%4.4f",a[0]);
 Form14->StringGrid1->Cells[1][1]=kpt;
        sprintf(kpt,"%4.4f",a[4*group+1]);
  Form14->StringGrid1->Cells[1][2]=kpt;
          sprintf(kpt,"%6.4f",a[1+4*g]);
   Form14->StringGrid1->Cells[1][3+4*g]=kpt;
   sprintf(kpt,"%4.2f",a[4*g+2]);
    Form14->StringGrid1->Cells[1][4+4*g]=kpt;
    sprintf(kpt,"%1.4f",2*a[4*g+3]);
       Form14->StringGrid1->Cells[1][5+4*g]=kpt;
       sprintf(kpt,"%6.4f",2*a[4*g+4]);
    Form14->StringGrid1->Cells[1][6+4*g]=kpt;

     Form14->StringGrid1->Cells[2][1]=sqrt(fabs(covar[0][0]));
  Form14->StringGrid1->Cells[2][2]=sqrt(fabs(covar[1+4*group][1+4*group]));
   Form14->StringGrid1->Cells[2][3+4*g]=sqrt(fabs(covar[1+4*g][1+4*g]));
    Form14->StringGrid1->Cells[2][4+4*g]=sqrt(fabs(covar[2+4*g][2+4*g]));
       Form14->StringGrid1->Cells[2][5+4*g]=sqrt(fabs(covar[3+4*g][3+4*g]));
    Form14->StringGrid1->Cells[2][6+4*g]=sqrt(fabs(covar[4+4*g][4+4*g]));
     sprintf(kpt,"%6.4f",chisq/upoints);
    Form14->Edit1->Text=kpt;
     Form14->StringGrid1->Refresh();
     Form14->Refresh();
   }

    SDIAppForm->Chart1->Refresh();

 // Inizio scrittura template
      TLocateOptions Opts;
  Opts.Clear();
   Opts << loPartialKey << loCaseInsensitive;

  int gg;
  g=-1;
  float sogl=atof(OKBottomDlg->Edit24->Text.c_str());

  for (gg=firstlin; gg <=lastlin;gg++)
  {
  g++;
  Form6->Table1->RecNo=gg+1;
       Form6->Table1->Edit();
     Form6->Table1->FieldValues["wavelen"]=origa[2+4*g];
           Form6->Table1->FieldValues["inte"]=Form14->Series1->YValues->Value[g];
      Form6->Table1->FieldValues["Fitwavelen"]=a[2+4*g];
    Form6->Table1->FieldValues["wg"]=2*a[3+4*g];
        Form6->Table1->FieldValues["wl"]=2*a[4+4*g];
Form6->Table1->FieldValues["error-inte"]=sqrt(fabs(covar[1+4*g][1+4*g]))*Form14->Series1->YValues->Value[g]/a[1+4*g];


 float er= sqrt(fabs(covar[1+4*g][1+4*g]))/a[1+4*g]*100.0;


if (Form6->Table1->FieldByName("Aki")->AsFloat ==-1.0)
 {
   Form6->Table1->FieldValues["Aki"]=0.0;
        SDIAppForm->Series4->ValueColor[Form6->Table1->RecNo-1]=clBlue;
 }
  else if (Form6->Table1->FieldByName("Aki")->AsFloat < 0 && Form6->Table1->FieldByName("Aki")->AsFloat !=-1.0)
 {
   Form6->Table1->FieldValues["Aki"]=-Form6->Table1->FieldByName("Aki")->AsFloat;
        SDIAppForm->Series4->ValueColor[Form6->Table1->RecNo-1]=clYellow;
   char lab[5];
    int ioniz=Form6->Table1->FieldByName("ion")->AsInteger;
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",Form6->Table1->FieldByName("specie")->AsString);
   break;
  case 2:
   sprintf(lab,"%s II",Form6->Table1->FieldByName("specie")->AsString);
  break;
  }
 SDIAppForm->Series4->XLabel[Form6->Table1->RecNo-1]=lab;
 }


       Form6->Table1->Post();
  }
  // Fine scrittura template


  // Chiusura

   SDIAppForm->Edit3->Text="0";
     free_vector(xx,0,upoints);
      free_vector(z,0,upoints);
       free_vector(sg,0,upoints);
        free_vector(a,0,na);
         free_vector(chi,0,na);
          free_vector(dyda,0,na);
           free_ivector(ia,0,na);
           free_matrix(alpha,0,na,0,na);
            free_matrix(covar,0,na,0,na);

   SDIAppForm->Series3->Clear();

   if ( SDIAppForm->Chart1->SeriesCount() > sc)
   {
   int sma=SDIAppForm->Chart1->SeriesCount();
   for (int su=sma-1; su > sc-1 ;su--)
   {
   SDIAppForm->Chart1->Series[su]->Free();
   }
   }

 //
    return;
   }
     //---------------------------------------------------------------------------
#define SQR(a) ((a)*(a))
void voigt0(float x,float* a,float* y,float* dyda,int m)
{
unsigned i,j;
static float sqrtln2=0.832554611;
static float sqrtpi=1.772453851;
float A[4],B[4],C[4],D[4],alpha[4],beta[4];
float dVdx=0.0,dVdy=0.0,V=0.0,X,Y,constant;
A[0]=-1.2150; B[0]= 1.2359; C[0]=-0.3085; D[0]= 0.0210;
A[1]=-1.3509; B[1]= 0.3786; C[1]= 0.5906; D[1]=-1.1858;
A[2]=-1.2150; B[2]=-1.2359; C[2]=-0.3085; D[2]=-0.0210;
A[3]=-1.3509; B[3]=-0.3786; C[3]= 0.5906; D[3]= 1.1858;

*y=a[0]+a[m]*x;
 dyda[0]=1.0;
  dyda[m]=x;

   for (i=1;i<m;i++) a[i]=fabs(a[i]);

   int npeaks=(m-1)/4.;
     float gmin= atof(OKBottomDlg->Edit16->Text.c_str());
for (i=0;i<npeaks;i++)
{
float ampl=a[1 + 4*i];
float pos=a[2 + 4*i];
float gamma_l=a[4 + 4*i];
   if (a[3 + 4*i] < gmin) a[3 + 4*i] = gmin;
float gamma_g=a[3 + 4*i];


X=(x-pos)*2*sqrtln2/gamma_g;
Y=gamma_l*sqrtln2/gamma_g;
constant=gamma_l*ampl*sqrtpi*sqrtln2/gamma_g;

for(j=0;j<=3;j++)
{
alpha[j]=C[j]*(Y-A[j])+D[j]*(X-B[j]);
beta[j]=SQR(Y-A[j])+SQR(X-B[j]);
V+=alpha[j]/beta[j];
dVdx+=D[j]/beta[j]-2.0*(X-B[j])*alpha[j]/SQR(beta[j]);
dVdy+=C[j]/beta[j]-2.0*(Y-A[j])*alpha[j]/SQR(beta[j]);
}
*y+=constant*V;
dyda[1 + 4*i]=constant*V/ampl;
dyda[2 + 4*i]=-constant*dVdx*2*sqrtln2/gamma_g;
dyda[4 + 4*i]=constant*(V/gamma_l+dVdy*sqrtln2/gamma_g);
dyda[3 + 4*i]=-constant*(V+(sqrtln2/gamma_g)*(2.0*(x-pos)*dVdx+gamma_l*dVdy))/gamma_g;
V=0;
dVdx=0;
dVdy=0;
}
}
#undef SQR
//---------------------------------------------------------------------------
#define SQR(a) ((a)*(a))
void voigt(float x, float a[], float *y, float dyda[], int na)
{

float aa[4]={-1.215,-1.3509,-1.215,-1.3509};
 float bb[4]={1.2359,0.3786,-1.2359,-0.3786};
  float cc[4]={-0.3085,0.5906,-0.3085,0.5906};
   float dd[4]={0.021,-1.1858,-0.021,1.1858};
   float alpha[4],beta[4];
    float dVdx=0.0,dVdy=0.0,V=0.0,X,Y,constant;
    int i,j,npeaks;
    static float sl2=0.832554611;
     static float sqrtpi=1.772453851;

npeaks=(na-1)/4.0;

   for (j=1;j<na;j++)
   {
    a[j]=fabs(a[j]);
   }


  *y=a[0]+a[na]*x;

 dyda[0]=1.0;
  dyda[na]=x;

for (j=0;j<npeaks;j++)
 {
      dyda[1+4*j]=0.0;
     dyda[2+4*j]=0.0;
      dyda[3+4*j]=0.0;
       dyda[4+4*j]=0.0;


X=(x-a[2 + 4*j])*sl2/a[3 + 4*j];
Y=a[4 + 4*j]*sl2/a[3 + 4*j];

for (i=0;i<=3;i++)
 {
alpha[i]=cc[i]*(Y-aa[i])+dd[i]*(X-bb[i]);
beta[i]=SQR(Y-aa[i])+SQR(X-bb[i]);
*y+=a[1 + 4*j]*alpha[i]/beta[i];

/*
 for (i=0;i<=3;i++)
 {
*y+=a[1 + 4*j]*(dd[i]*(-bb[i] +
         (x - a[2 + 4*j])*sl2/a[3+4*j]) +
      cc[i]*(-aa[i] + a[4+4*j]*sl2/a[3+4*j]))/
   (SQR(-bb[i] + (x - a[2 + 4*j])*sl2/a[3+4*j]) +
     SQR(-aa[i] + a[4+4*j]*sl2/a[3+4*j]));
 */
  
dyda[1+4*j]+=(dd[i]*(-bb[i] +
         (x - a[2 + 4*j])*sl2/a[3+4*j]) +
      cc[i]*(-aa[i] + a[4+4*j]*sl2/a[3+4*j]))/
   (pow(-bb[i] + (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
     pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2));

 dyda[2+4*j]+=-(a[1 + 4*j]*dd[i]*sl2/
      (a[3 + 4*j]*(pow(-bb[i] +
            (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
          pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2)))) +
   2.0*a[1 + 4*j]*(dd[i]*(-bb[i] +
          (x - a[2 + 4*j])*sl2/a[3+4*j]) +
       cc[i]*(-aa[i] + a[4+4*j]*sl2/a[3+4*j]))*
     (-bb[i] + (x - a[2 + 4*j])*sl2/a[3+4*j])*sl2/
    (a[3+4*j]*pow(pow(-bb[i] +
          (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
        pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2),2));

  dyda[3+4*j]+=-(a[1 + 4*j]*(dd[i]*(-bb[i] +
            (x - a[2 + 4*j])*sl2/a[3+4*j]) +
         cc[i]*(-aa[i] + a[4+4*j]*sl2/a[3+4*j]))*
       (2.0*(x - a[2 + 4*j])*(a[3+4*j]*bb[i] - x*sl2 +
             a[2 + 4*j]*sl2)*sl2/pow(a[3+4*j],3)
           + 2*a[4+4*j]*(a[3+4*j]*aa[i] -
             a[4+4*j]*sl2)*sl2/pow(a[3+4*j],3)
         )/pow(pow(-bb[i] +
          (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
        pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2),2)) +
   a[1 + 4*j]*(-(a[4+4*j]*cc[i]) - x*dd[i] + a[2 + 4*j]*dd[i])*
     sl2/
    (pow(a[3+4*j],2)*(pow(-bb[i] +
          (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
        pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2)));

   dyda[4+4*j]+=a[1 + 4*j]*cc[i]*sl2/
    (a[3+4*j]*(pow(-bb[i] +
          (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
        pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2))) -
   2.0*a[1 + 4*j]*(dd[i]*(-bb[i] +
          (x - a[2 + 4*j])*sl2/a[3+4*j]) +
       cc[i]*(-aa[i] + a[4+4*j]*sl2/a[3+4*j]))*
     (-aa[i] + a[4+4*j]*sl2/a[3+4*j])*sl2/
    (a[3+4*j]*pow(pow(-bb[i] +
          (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
        pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2),2));
  }
  }
/*
float a1=-1.1317;
 float a2=-1.2278;
  float B1=0.905;
   float c1=-0.3277;
    float c2=1.2197;
     float d1=-.4175;

    int j,npeaks;
    float sl2,beta,f11,f22,f12,f21,f23,v1,v2,v3;

npeaks=(na-1)/4.0;


   for (j=1;j<na;j++)
   {
    a[j]=fabs(a[j]);
   }

  *y=a[0]+a[na]*x;

 dyda[0]=1.0;
  dyda[na]=x;

         sl2= sqrt(log(2.0));

for (j=0;j<npeaks;j++)
 {
 beta=a[3+4*j]/sl2;
 f11=a[4+4*j]/beta-a1;
 f12=a[4+4*j]/beta-a2;
 f22=(x-a[2 + 4*j])/beta;
 f21=f22-B1;
 f23=f22+B1;
 v1=(c1*f11+d1*f21)/(f11*f11+f21*f21);
  v2=c2*f12/(f12*f12+f22*f22);
   v3=(c1*f11-d1*f23)/(f11*f11+f23*f23);
   *y+=a[1+4*j]/a[3+4*j]*(v1+v2+v3);

dyda[1+4*j]=(v1+v2+v3)/a[3+4*j];

 dyda[2+4*j]= a[1+4*j]/a[3+4*j]*(-((d1*sl2)/(a[3+4*j]*(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2)))) +
     (d1*sl2)/(a[3+4*j]*(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2))) +
     (2*sl2*(c1*(-a1 + (sl2*a[4+4*j])/a[3+4*j]) + d1*(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j]))*(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j]))/
      (a[3+4*j]*pow(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2),2)) +
     (2*sl2*(c1*(-a1 + (sl2*a[4+4*j])/a[3+4*j]) - d1*(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j]))*(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j]))/
      (a[3+4*j]*pow(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2),2)) +
     (2*c2*pow(sl2,2)*(-a2 + (sl2*a[4+4*j])/a[3+4*j])*(x - a[2+4*j]))/
      (pow(a[3+4*j],2)*pow(pow(-a2 + (sl2*a[4+4*j])/a[3+4*j],2) + (pow(sl2,2)*pow(x - a[2+4*j],2))/pow(a[3+4*j],2),
         2)));

  dyda[3+4*j]=a[1+4*j]/a[3+4*j]*((-((c1*sl2*a[4+4*j])/pow(a[3+4*j],2)) - (d1*sl2*(x - a[2+4*j]))/pow(a[3+4*j],2))/
      (pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2)) +
     (-((c1*sl2*a[4+4*j])/pow(a[3+4*j],2)) + (d1*sl2*(x - a[2+4*j]))/pow(a[3+4*j],2))/
      (pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2)) -
     ((c1*(-a1 + (sl2*a[4+4*j])/a[3+4*j]) + d1*(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j]))*
        ((-2*sl2*a[4+4*j]*(-a1 + (sl2*a[4+4*j])/a[3+4*j]))/pow(a[3+4*j],2) -
          (2*sl2*(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j])*(x - a[2+4*j]))/pow(a[3+4*j],2)))/
      pow(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2),2) -
     ((c1*(-a1 + (sl2*a[4+4*j])/a[3+4*j]) - d1*(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j]))*
        ((-2*sl2*a[4+4*j]*(-a1 + (sl2*a[4+4*j])/a[3+4*j]))/pow(a[3+4*j],2) -
          (2*sl2*(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j])*(x - a[2+4*j]))/pow(a[3+4*j],2)))/
      pow(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2),2) -
     (c2*(-a2 + (sl2*a[4+4*j])/a[3+4*j])*((-2*sl2*a[4+4*j]*(-a2 + (sl2*a[4+4*j])/a[3+4*j]))/pow(a[3+4*j],2) -
          (2*pow(sl2,2)*pow(x - a[2+4*j],2))/pow(a[3+4*j],3)))/
      pow(pow(-a2 + (sl2*a[4+4*j])/a[3+4*j],2) + (pow(sl2,2)*pow(x - a[2+4*j],2))/pow(a[3+4*j],2),2) -
     (c2*sl2*a[4+4*j])/(pow(a[3+4*j],2)*(pow(-a2 + (sl2*a[4+4*j])/a[3+4*j],2) +
          (pow(sl2,2)*pow(x - a[2+4*j],2))/pow(a[3+4*j],2))))-a[1+4*j]/(a[3+4*j]*a[3+4*j])*(v1+v2+v3);

   dyda[4+4*j]= a[1+4*j]/a[3+4*j]*((-2*sl2*(-a1 + (sl2*a[4+4*j])/a[3+4*j])*(c1*(-a1 + (sl2*a[4+4*j])/a[3+4*j]) + d1*(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j])))/
      (a[3+4*j]*pow(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2),2)) +
     (c1*sl2)/(a[3+4*j]*(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(-B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2))) -
     (2*sl2*(-a1 + (sl2*a[4+4*j])/a[3+4*j])*(c1*(-a1 + (sl2*a[4+4*j])/a[3+4*j]) - d1*(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j])))/
      (a[3+4*j]*pow(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2),2)) +
     (c1*sl2)/(a[3+4*j]*(pow(-a1 + (sl2*a[4+4*j])/a[3+4*j],2) + pow(B1 + (sl2*(x - a[2+4*j]))/a[3+4*j],2))) -
     (2*c2*sl2*pow(-a2 + (sl2*a[4+4*j])/a[3+4*j],2))/
      (a[3+4*j]*pow(pow(-a2 + (sl2*a[4+4*j])/a[3+4*j],2) + (pow(sl2,2)*pow(x - a[2+4*j],2))/pow(a[3+4*j],2),2)) +
     (c2*sl2)/(a[3+4*j]*(pow(-a2 + (sl2*a[4+4*j])/a[3+4*j],2) + (pow(sl2,2)*pow(x - a[2+4*j],2))/pow(a[3+4*j],2))));
  }
   */

 }
#undef SQR
//---------------------------------------------------------------------------
#define SQR(a)((a)*(a))
void plotvoigt0(float x, float a[], float* y, int na)
{
 int colo[34]={clWhite,clRed,clYellow,clGreen,clMaroon,clDkGray,clOlive,clPurple,clLtGray,clBlue,clNavy,clBlack,clFuchsia,clGray,clTeal,clSilver,clLime,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};


    int i,j;
    static float sqrtln2=0.832554611;
     static float sqrtpi=1.772453851;


  *y=a[0]+a[na]*x;

   int group=(na-1)/4.0;

    int sc=atoi((SDIAppForm->Edit13->Text).c_str());
     SDIAppForm->Chart1->Series[sc]->AddXY(x,*y,' ',colo[0]);

    int ct=-1;
 float A[4],B[4],C[4],D[4],alpha[4],beta[4];
float dVdx=0.0,dVdy=0.0,V=0.0,X,Y,constant;
A[0]=-1.2150; B[0]= 1.2359; C[0]=-0.3085; D[0]= 0.0210;
A[1]=-1.3509; B[1]= 0.3786; C[1]= 0.5906; D[1]=-1.1858;
A[2]=-1.2150; B[2]=-1.2359; C[2]=-0.3085; D[2]=-0.0210;
A[3]=-1.3509; B[3]=-0.3786; C[3]= 0.5906; D[3]= 1.1858;



   int npeaks=(na-1)/4.;

for (i=0;i<npeaks;i++)
{
*y=0;
V=0;
float ampl=a[1 + 4*i];
float pos=a[2 + 4*i];
float gamma_l=a[4 + 4*i];
float gamma_g=a[3 + 4*i];

X=(x-pos)*2*sqrtln2/gamma_g;
Y=gamma_l*sqrtln2/gamma_g;
constant=gamma_l*ampl*sqrtpi*sqrtln2/gamma_g;

for(j=0;j<=3;j++)
{
alpha[j]=C[j]*(Y-A[j])+D[j]*(X-B[j]);
beta[j]=SQR(Y-A[j])+SQR(X-B[j]);
V+=alpha[j]/beta[j];
}
*y+=constant*V;
ct++;
  SDIAppForm->Chart1->Series[sc+ct+1]->Active=true;
 SDIAppForm->Chart1->Series[sc+ct+1]->AddXY(x,*y,' ',colo[ct+1]);
  }
 }

 #undef SQR
//---------------------------------------------------------------------------
#define SQR(a)((a)*(a))
void plotvoigt(float x, float* a, float* y, int na)
{
 int colo[34]={clSilver,clRed,clYellow,clGreen,clMaroon,clDkGray,clOlive,clPurple,clLtGray,clBlue,clNavy,clBlack,clFuchsia,clGray,clTeal,clSilver,clLime,clRed+200,clGray+200,clYellow+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
  float aa[4]={-1.215,-1.3509,-1.215,-1.3509};
 float bb[4]={1.2359,0.3786,-1.2359,-0.3786};
  float cc[4]={-0.3085,0.5906,-0.3085,0.5906};
   float dd[4]={0.021,-1.1858,-0.021,1.1858};

    int i,j;
    static float sl2=0.832554611;
     static float sqrtpi=1.772453851;


  *y=a[0]+a[na]*x;

   int group=(na-1)/4.0;

    int sc=atoi((SDIAppForm->Edit13->Text).c_str());
     SDIAppForm->Chart1->Series[sc]->AddXY(x,*y,' ',colo[0]);

    int ct=-1;
 for (j=0;j<group;j++)
 {
 /*
 V=0;
X=(x-a[i+1])*2*sqrtln2/a[i+3];
Y=a[i+2]*sqrtln2/a[i+3];
constant=a[i+2]*a[i]*sqrtpi*sqrtln2/a[i+3];
for(j=0;j<=3;j++)
{
alpha[j]=C[j]*(Y-A[j])+D[j]*(X-B[j]);
beta[j]=SQR(Y-A[j])+SQR(X-B[j]);
V+=alpha[j]/beta[j];
  }
*y=constant*V;
*/

 *y=0;
 for (i=0;i<=3;i++)
 {
*y+=a[1 + 4*j]*(dd[i]*(-bb[i] +
         (x - a[2 + 4*j])*sl2/a[3+4*j]) +
      cc[i]*(-aa[i] + a[4+4*j]*sl2/a[3+4*j]))/
   (pow(-bb[i] + (x - a[2 + 4*j])*sl2/a[3+4*j],2) +
     pow(-aa[i] + a[4+4*j]*sl2/a[3+4*j],2));
 }
ct++;
  SDIAppForm->Chart1->Series[sc+ct+1]->Active=true;
 SDIAppForm->Chart1->Series[sc+ct+1]->AddXY(x,*y,' ',colo[ct+1]);
  }
 }

 #undef SQR
 //---------------------------------------------------------------------------
#define SQR(a)((a)*(a))
 double integrale0(float x, float w[])
{
 float aa[4]={-1.215,-1.3509,-1.215,-1.3509};
 float bb[4]={1.2359,0.3786,-1.2359,-0.3786};
  float cc[4]={-0.3085,0.5906,-0.3085,0.5906};
   float dd[4]={0.021,-1.1858,-0.021,1.1858};

    int i;

    float sl2,sqrtpi;

     double y;

         sl2= sqrt(log(2.0));
         sqrtpi=sqrt(3.14151);

float constant=w[2]*sqrtpi*sl2/w[3];

  for (i=0;i<4;i++)
 {
  y+=(w[0]*w[2]*(2.*atan((2*sl2*x - 2*sl2*w[1] - w[2]*bb[i])/
          (sl2*w[3] - w[2]*aa[i]))*cc[i] +
       dd[i]*log(SQR(sl2)*
           (SQR(x) - 2*x*w[1] + SQR(w[1]) +
             SQR(w[3])) - 2*sl2*w[2]*w[3]*aa[i] +
          SQR(w[2]*aa[i]) +
          4*sl2*(-x + w[1])*w[2]*bb[i] +
          SQR(w[2]*bb[i]))))/(4.*sl2);
  }

  return y*constant;
  }
 #undef SQR
//---------------------------------------------------------------------------
double integrale(float x, float w[])
{
 float aa[4]={-1.215,-1.3509,-1.215,-1.3509};
 float bb[4]={1.2359,0.3786,-1.2359,-0.3786};
  float cc[4]={-0.3085,0.5906,-0.3085,0.5906};
   float dd[4]={0.021,-1.1858,-0.021,1.1858};

    int i;

    float sl2,sqrtpi;

     double y;

     sl2= sqrt(log(2.0));


  for (i=0;i<4;i++)
 {
  y+=(w[0]*w[2]*
        (2.*atan((sl2*(x - w[1]) - w[2]*bb[i])/
          (sl2*w[3] - w[2]*aa[i]))*cc[i] +
       dd[i]*log(pow(sl2,2)*
           (pow(x-w[1],2) +
             pow(w[3],2)) -
          2*sl2*w[2]*w[3]*aa[i] +
          pow(w[2],2)*pow(aa[i],2) +
          2*sl2*(-x + w[1])*w[2]*bb[i] +
          pow(w[2],2)*pow(bb[i],2))))/
  (2.*sl2);
  }


  return y;
  }



void __fastcall TSDIAppForm::ToolButton3Click(TObject *Sender)
{
void compfile(AnsiString nomefile);

  OpenDialog->FileName = "";
     OpenDialog->Filter = "Mechelle Files (*.mch)|*.MCH|All Files (*.*)|*.*";

     AnsiString fp;
     OpenDialog->InitialDir=SDIAppForm->Edit14->Text;

    if (OpenDialog->Execute())
  {
  SaveDialog->FileName = OpenDialog->FileName;

   for (int y=1;y<Form13->StringGrid1->RowCount;y++)
     {
     if (Form13->StringGrid1->Cells[1][y]=="")
    {
    Form13->StringGrid1->Cells[1][y]=OpenDialog->FileName;
    Form13->StringGrid1->Refresh();
    break;
    }
      }

  compfile(OpenDialog->FileName);
        fp=(ExtractFilePath(OpenDialog->FileName));
       SDIAppForm->Edit14->Text=fp;
  }        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ToolButton7Click(TObject *Sender)
{
Form13->StringGrid1->ColWidths[0]=12;
Form13->StringGrid1->ColWidths[1]=400;
Form13->Edit1->Text="";
Form13->Show();        
}
//---------------------------------------------------------------------------


void __fastcall TSDIAppForm::ChangeBackground1Click(TObject *Sender)
{
int colore;
     SDIAppForm->ColorDialog1->Color=SDIAppForm->Chart1->BackColor;
    if (SDIAppForm->ColorDialog1->Execute())
    colore = SDIAppForm->ColorDialog1->Color;
    SDIAppForm->Chart1->BackColor=colore;
    return;
}
//---------------------------------------------------------------------------







void __fastcall TSDIAppForm::ShowSpectraList2Click(TObject *Sender)
{
Form13->StringGrid1->ColWidths[0]=12;
Form13->StringGrid1->ColWidths[1]=400;
Form13->Edit1->Text="";
Form13->Show();
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Compare2Click(TObject *Sender)
{
void compfile(AnsiString nomefile);

  OpenDialog->FileName = "";
     OpenDialog->Filter = "Mechelle Files (*.mch)|*.MCH|All Files (*.*)|*.*";

     AnsiString fp;
     OpenDialog->InitialDir=SDIAppForm->Edit14->Text;

    if (OpenDialog->Execute())
  {
  SaveDialog->FileName = OpenDialog->FileName;

   for (int y=1;y<Form13->StringGrid1->RowCount;y++)
     {
     if (Form13->StringGrid1->Cells[1][y]=="")
    {
    Form13->StringGrid1->Cells[1][y]=OpenDialog->FileName;
    Form13->StringGrid1->Refresh();
    break;
    }
      }

  compfile(OpenDialog->FileName);
   fp=(ExtractFilePath(OpenDialog->FileName));
       SDIAppForm->Edit14->Text=fp;
  }                
}
//---------------------------------------------------------------------------



void __fastcall TSDIAppForm::N3DOnoff1Click(TObject *Sender)
{
   if (SDIAppForm->Chart1->View3D==false)  {SDIAppForm->Chart1->View3D=true;
   N3DOnoff1->Checked=true;}
   else
   {SDIAppForm->Chart1->View3D=false;
   N3DOnoff1->Checked=false;}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ChangeBackground2Click(TObject *Sender)
{
int colore;
   {
   SDIAppForm->ColorDialog1->Color=SDIAppForm->Chart1->BackColor;
    if (SDIAppForm->ColorDialog1->Execute())
    colore = SDIAppForm->ColorDialog1->Color;
    SDIAppForm->Chart1->BackColor=colore;
    }
    return;        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::LogYOnOff2Click(TObject *Sender)
{
  if (SDIAppForm->Chart1->LeftAxis->Logarithmic==false)  {SDIAppForm->Chart1->LeftAxis->Logarithmic=true;
        LogYOnOff2->Checked=true;
  }
   else
   {SDIAppForm->Chart1->LeftAxis->Logarithmic=false;
     LogYOnOff2->Checked=false;
   }
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::GridXOnOff1Click(TObject *Sender)
{
  if (SDIAppForm->Chart1->BottomAxis->Grid->Visible==false)
 { SDIAppForm->Chart1->BottomAxis->Grid->Visible=true;
 GridXOnOff1->Checked=true;
  }
   else
  {
  SDIAppForm->Chart1->BottomAxis->Grid->Visible=false;
  GridXOnOff1->Checked=false;
   }
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::LOgXOnOff2Click(TObject *Sender)
{
  if (SDIAppForm->Chart1->BottomAxis->Logarithmic==false)  {SDIAppForm->Chart1->BottomAxis->Logarithmic=true;
  LOgXOnOff2->Checked=true; }
   else
 {  SDIAppForm->Chart1->BottomAxis->Logarithmic=false;
 LOgXOnOff2->Checked=false;}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::GridYOnOff1Click(TObject *Sender)
{
  if (SDIAppForm->Chart1->LeftAxis->Grid->Visible==false)  {SDIAppForm->Chart1->LeftAxis->Grid->Visible=true;
       GridYOnOff1->Checked=true;
  }
   else
   {
   SDIAppForm->Chart1->LeftAxis->Grid->Visible=false;
          GridYOnOff1->Checked=false;
  }
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::AnimatedZoomOnOff2Click(TObject *Sender)
{
 if (SDIAppForm->Chart1->AnimatedZoom==false)  {SDIAppForm->Chart1->AnimatedZoom=true;
   AnimatedZoomOnOff2->Checked=true;}
   else
   {SDIAppForm->Chart1->AnimatedZoom=false;
   AnimatedZoomOnOff2->Checked=false;}
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ShowLabels2Click(TObject *Sender)
{
if (ShowLabels2->Checked==true)
{
Series4->Marks->Visible=false;
ShowLabels2->Checked=false;
}
else
{
Series4->Marks->Visible=true;
ShowLabels2->Checked=true;
}        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ClearGraph2Click(TObject *Sender)
{
for (int j=0;j<6;j++)
{
SDIAppForm->Chart1->Series[j]->Clear();
}

     AnsiString nm;
      AnsiString cp="";
    int u,k;
   int sercont=SDIAppForm->Chart1->SeriesCount();
ex:
   for (u=0; u < SDIAppForm->Chart1->SeriesCount() ;u++)
   {
   nm=SDIAppForm->Chart1->Series[u]->Name;
    for (k=1; k < sercont+1 ;k++)
   {
   cp="";
       cp.cat_sprintf("s%i",k);
    if (nm == cp)
   {
    SDIAppForm->Chart1->Series[u]->Free();
    goto ex;
    }
    }
 }


 for (int j=0;j<=Form13->StringGrid1->RowCount;j++)
 {
  Form13->StringGrid1->Cells[0][j]="";
 Form13->StringGrid1->Cells[1][j]="";
 }
  Form13->Edit1->Text="";
    Form13->StringGrid1->Refresh();
  SDIAppForm->Caption ="LIBS++";
 Chart1->BottomAxis->Automatic=true;
  Chart1->LeftAxis->Automatic=true;        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::AutoScaleX1Click(TObject *Sender)
{
 Chart1->BottomAxis->Automatic=true;        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::AutoScaleY1Click(TObject *Sender)
{
  Chart1->LeftAxis->Automatic=true;        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::ShowAll2Click(TObject *Sender)
{
 Chart1->BottomAxis->Automatic=true;
  Chart1->LeftAxis->Automatic=true;        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::N6Click(TObject *Sender)
{
  OKBottomDlg->Show();        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Gradient1Click(TObject *Sender)
{
if (SDIAppForm->Chart1->Gradient->Visible==false)
{SDIAppForm->Chart1->Gradient->Visible=true;
 Gradient1->Checked=true;
}
else
{SDIAppForm->Chart1->Gradient->Visible=false;
Gradient1->Checked=false;
}
}
//---------------------------------------------------------------------------



void __fastcall TSDIAppForm::Button3Click(TObject *Sender)
{
   /* swap (Series1,Series2);
  Series2->Active=false;
  Series1->Active=true;

  if (Series5->Count() == Series4->Count())
  {
  swap(Series4,Series5);
  }
    Series5->Active=false;
  Series4->Active=true;
  */
  void showsboltz();
showsboltz();        
}
//---------------------------------------------------------------------------

void __fastcall TSDIAppForm::Button8Click(TObject *Sender)
{
// Form20->Show();
       for (int w=1; w<=Form27->StringGrid2->RowCount;w++)
                {
                Form27->StringGrid2->Cells[0][w]="";
                Form27->StringGrid2->Cells[1][w]="";
                Form27->StringGrid2->Cells[2][w]="";
                Form27->StringGrid2->Cells[3][w]="";
                Form27->StringGrid2->Cells[4][w]="";
                }
                
  void showsahaboltz();
showsahaboltz();

for (int i=1;i< Form27->StringGrid2->RowCount;i++)
{
if (Form27->StringGrid2->Cells[1][i]!="") Form27->StringGrid2->Cells[0][i]="X";
}
   Form27->Refresh();
}
//---------------------------------------------------------------------------

