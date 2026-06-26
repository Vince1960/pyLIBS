//---------------------------------------------------------------------------
#pragma hdrstop
#include <vcl.h>
#include <fstream.h>
#include <math.h>
#include "Unit1.h"
#include "Unit6.h"
#include "Unit9.h"
#include "Unit20.h"
#include "Unit21.h"
#include "Unit22.h"
static double glfatt,glne,gleion;
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm20 *Form20;
//---------------------------------------------------------------------------
__fastcall TForm20::TForm20(TComponent* Owner)
    : TForm(Owner)
{

}
//---------------------------------------------------------------------------



void __fastcall TForm20::StringGrid1SelectCell(TObject *Sender, int Col,
      int Row, bool &CanSelect)
{
if (StringGrid1->Cells[0][Row]=="X")
{
StringGrid1->Cells[0][Row]="";
}
else
{
StringGrid1->Cells[0][Row]="X";
}
}
//---------------------------------------------------------------------------

void __fastcall TForm20::Button2Click(TObject *Sender)
{
for (int i=1; i < Form20->StringGrid1->RowCount;i++)
{
Form20->StringGrid1->Cells[0][i]="";
}
}
//---------------------------------------------------------------------------

void __fastcall TForm20::Button3Click(TObject *Sender)
{
for (int i=1; i < Form20->StringGrid1->RowCount;i++)
{
Form20->StringGrid1->Cells[0][i]="X";
}
}
//---------------------------------------------------------------------------

void __fastcall TForm20::Button4Click(TObject *Sender)
{
Form20->Close();
}
//---------------------------------------------------------------------------

void __fastcall TForm20::Button1Click(TObject *Sender)
{
float rtbis(double (*func)(double), double x1, double x2, float xacc);
double testark(double x);
double tot=0;
 int cnt=0;
  float pop1,z1,t1;
    float pop2,z2,t2;
   Form9->Edit8->Text="";
/*
  Form22->StringGrid1->ColWidths[0]=20;
    Form22->StringGrid1->RowCount=2;
  Form22->StringGrid1->RowCount=Form9->StringGrid2->RowCount;
  Form22->StringGrid1->Cells[0][0]="Sel.";
  Form22->StringGrid1->Cells[0][1]="";
  Form22->StringGrid1->Cells[1][0]="Element";
  Form22->StringGrid1->Cells[2][0]="TStark";
  Form22->StringGrid1->Refresh();
 Form22->Show();
 */
int jcount=0;
  for (int i=1; i < Form20->StringGrid1->RowCount; i++)
{
if (Form20->StringGrid1->Cells[0][i] != "X" && atof(AnsiString(Form20->StringGrid1->Cells[4][i]).c_str()) !=0.0)
{
cnt++;
 tot+=atof(AnsiString(Form20->StringGrid1->Cells[4][i]).c_str());
}
}
if (cnt !=0)
{
char dm[20];
sprintf(dm,"%1.2E",tot/cnt);
Form9->RadioGroup2->ItemIndex=2;
 Form9->Edit2->Text=dm;
 for (int j=0; j < Form9->StringGrid2->RowCount; j++)
 {
 Form9->StringGrid2->Cells[2][j+1]="";
 Form9->StringGrid2->Cells[3][j+1]="";
 Form9->StringGrid2->Cells[4][j+1]=dm;
 Form9->StringGrid2->Cells[5][j+1]="";
 }
 Form9->StringGrid2->Refresh();
/*
 // Ricalcolo TStark
float soglia=atof(OKBottomDlg->Edit17->Text.c_str());
char sqls[300];
 char sname[10];
 sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki > %f AND inte > 0.0  ORDER BY specie",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),soglia);
Form9->Query2->SQL->Clear();
Form9->Query2->SQL->Add(sqls);
Form9->Query2->Open();
Form9->Query2->First();
int deg1,deg2;
  double saha,eion;
 for (int i=0; i < Form9->Query2->RecordCount;i++)
{

// Cerco stato neutro
   AnsiString ppp=Form9->Query2->FieldValues["specie"];
   sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=1 AND aki > 0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);
 Form9->Query6->SQL->Clear();
Form9->Query6->SQL->Add(sqls);
Form9->Query6->Open();
  Form9->Query6->First();
int lin1=Form9->Query6->RecordCount;

 sprintf(sname,"%sI",Trim(ppp).c_str());
 Form9->Query1->First();

 for (int j=0; j < Form9->Query1->RecordCount;j++)
 {
  if  ((Form9->StringGrid1->Cells[1][j+1]==sname))
  {
  t1=atof(Form9->StringGrid1->Cells[3][j+1].c_str());
  pop1=atof(Form9->StringGrid1->Cells[4][j+1].c_str());
  z1=atof(Form9->StringGrid1->Cells[5][j+1].c_str());
  }
  Form9->Query1->Next();
 }

// Cerco stato ionizzato

   sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=2 AND aki >0 AND inte > 0.0",AnsiString(ExtractFileName(Form6->Table1->TableName)).c_str(),ppp);

 Form9->Query6->SQL->Clear();
Form9->Query6->SQL->Add(sqls);
Form9->Query6->Open();
  Form9->Query6->First();
int lin2=Form9->Query6->RecordCount;
 sprintf(sname,"%sII",Trim(ppp).c_str());

 Form9->Query1->First();

 for (int j=0; j < Form9->Query1->RecordCount;j++)
 {
  if  ((Form9->StringGrid1->Cells[1][j+1]==sname))
  {
  t2=atof(Form9->StringGrid1->Cells[3][j+1].c_str());
  pop2=atof(Form9->StringGrid1->Cells[4][j+1].c_str());
   z2=atof(Form9->StringGrid1->Cells[5][j+1].c_str());
  }
  Form9->Query1->Next();
 }
// Se ci sono I e II calcolo TStark per l'elemento

 if ((lin1*lin2) !=0)
 {
sprintf(sqls,"SELECT DISTINCT Ei,gi FROM %s WHERE Ei=0.0 AND ion=1 ORDER BY Ei",Form9->StringGrid2->Cells[1][i+1]);

  Form9->Query4->SQL->Clear();
Form9->Query4->SQL->Add(sqls);
Form9->Query4->Open();
  Form9->Query4->First();
  if (Form9->Query4->RecordCount > 0)
{
deg1=Form9->Query4->FieldValues["gi"];
}
else
{
deg1=1;
}
 sprintf(sqls,"SELECT DISTINCT Ei,gi FROM %s WHERE Ei=0.0 AND ion=2 ORDER BY Ei",Form9->StringGrid2->Cells[1][i+1]);

 Form9->Query4->SQL->Clear();
Form9->Query4->SQL->Add(sqls);
Form9->Query4->Open();
  Form9->Query4->First();
  if (Form9->Query4->RecordCount > 0)
{
deg2=Form9->Query4->FieldValues["gi"];
}
else
{
deg2=1;
}
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

 gleion=eion;
  glfatt=(6.04e+21)*exp(pop1-pop2);
   glne=tot/cnt;
 float xacc=0.001;
  double lim1=atof(OKBottomDlg->Edit20->Text.c_str());
   double lim2=atof(OKBottomDlg->Edit21->Text.c_str());
  double kstark=rtbis(testark,lim1,lim2,xacc);
  jcount++;
  Form22->StringGrid1->Cells[1][jcount]=Trim(ppp);
  Form22->StringGrid1->Cells[2][jcount]=kstark;
 }
 Form9->Query2->Next();
 }

 // Ho calcolato TStark

 Form9->Edit12->Text=dm;
}
*/
}
}
//---------------------------------------------------------------------------

void __fastcall TForm20::FormActivate(TObject *Sender)
{
   Form21->Close();
}
//---------------------------------------------------------------------------

double testark(double x)
{
   return glfatt*pow(x,1.5)*exp(-gleion/x)-glne;
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

void __fastcall TForm20::FormClose(TObject *Sender, TCloseAction &Action)
{
for (int w=1; w<=Form20->StringGrid1->RowCount;w++)
{
Form20->StringGrid1->Cells[1][w]="";
Form20->StringGrid1->Cells[2][w]="";
Form20->StringGrid1->Cells[3][w]="";
Form20->StringGrid1->Cells[4][w]="";
Form20->StringGrid1->Cells[5][w]="";
Form20->StringGrid1->Cells[6][w]="";
}
}
//---------------------------------------------------------------------------

