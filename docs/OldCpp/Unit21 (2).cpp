//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include <math.h>
#include <fstream.h>
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
#include "Unit21.h"
#include "Unit23.h"
#include "Unit25.h"
#include "Unit27.h"
static double knu0;
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm21 *Form21;
//---------------------------------------------------------------------------
__fastcall TForm21::TForm21(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm21::Copy1Click(TObject *Sender)
{
 Graphics::TBitmap *FormImage;
 TClipboard *MyClip;

	MyClip = new TClipboard();

	FormImage = GetFormImage();
	MyClip->Assign(FormImage);      
}
//---------------------------------------------------------------------------
void __fastcall TForm21::Print1Click(TObject *Sender)
{
if (PrintDialog1 ->Execute())
{
  Chart1->Print();
}
}
//---------------------------------------------------------------------------

void __fastcall TForm21::Button4Click(TObject *Sender)
{
float rtbis(double (*func)(double), double x1, double x2, float xacc);
double fun(double x);
double zZ(AnsiString spp,int i,float ti);
Form21->Hide();
// int iter=atoi(Form21->Edit2->Text.c_str());
Form23->Show();

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
                Form23->StringGrid1->ColWidths[0]=20;
  Form23->StringGrid1->Cells[1][0]="Species";
  Form23->StringGrid1->Cells[2][0]="Wavel.";
  Form23->StringGrid1->Cells[3][0]="Corr.";
  Form23->StringGrid1->Cells[4][0]="Wl";
  Form23->StringGrid1->Cells[5][0]="Wl0";
  char sqls[300];
    Form23->StringGrid1->RowCount=2;

    sprintf(sqls,"SELECT DISTINCT specie,ion FROM %s WHERE aki !=0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie,ion",ExtractFileName(Form6->Table1->TableName));
        Form9->Query1->SQL->Clear();
        Form9->Query1->SQL->Add(sqls);
    sprintf(sqls,"SELECT DISTINCT specie FROM %s WHERE aki !=0.0 AND aki != -1.0 AND inte > 0.0 ORDER BY specie",ExtractFileName(Form6->Table1->TableName));
        Form9->Query2->SQL->Clear();
        Form9->Query2->SQL->Add(sqls);
         Form9->Query1->Open();
         Form9->Query2->Open();
         
char sname[32];


{
     int progre=0;


Form9->Query1->First();
Form9->Query2->First();




 for (int i=0; i < Form9->Query1->RecordCount; i++)
 {

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


sprintf(sqls,"SELECT * FROM %s WHERE specie='%s' AND ion=%s AND aki !=0.0 AND aki != -1.0 AND inte > 0.0",ExtractFileName(Form6->Table1->TableName),Form9->Edit3->Text,Form9->Edit4->Text);
Form9->Query3->SQL->Clear();
Form9->Query3->SQL->Add(sqls);
Form9->Query3->Open();
Form9->Query3->First();

   int reco= Form9->Query3->RecordCount;

   for (int j=0; j < reco; j++)
{
 progre++;
  Form23->StringGrid1->RowCount++;
 float wave=Form9->Query3->FieldValues["asswavelen"];
  float inte=Form9->Query3->FieldValues["inte"];
 float erro= Form9->Query3->FieldValues["error-inte"];
   float aki= Form9->Query3->FieldValues["aki"];
    int gk= Form9->Query3->FieldValues["gk"];
     int gi= Form9->Query3->FieldValues["gi"];
     float Ek= Form9->Query3->FieldValues["Ek"];
 char tmd[10];
 sprintf(tmd,"%1.2f",wave);
Form23->StringGrid1->Cells[1][progre]=sname;
Form23->StringGrid1->Cells[2][progre]=tmd;
sprintf(sqls,"SELECT * FROM elementi WHERE [specie]='%s'",Trim(Form9->Edit3->Text));
        Form9->Query5->SQL->Clear();
        Form9->Query5->SQL->Add(sqls);
        Form9->Query5->Open();
float ma=Form9->Query5->FieldValues["m_atomica"];
float Eio=Form9->Query5->FieldValues["en_ion"];
double tmp=atof(Form9->Edit7->Text.c_str())*11600.0;
double denel=atof(Form9->Edit8->Text.c_str());
float aut;

 if (atof(Form23->StringGrid1->Cells[3][progre].c_str()) != 0.0)
  aut=atof(Form23->StringGrid1->Cells[3][progre].c_str());
  else
  aut=1.0;

// double gau=wave*sqrt(tmp)*4.17E-8/sqrt(ma);
//Larghezza (Dlambda) Doppler

double lor=fabs(Form9->Query3->FieldByName("wl")->AsFloat);
double wgau=fabs(Form9->Query3->FieldByName("wg")->AsFloat);

double wtot=sqrt(pow(lor/2,2)+pow(wgau,2))+lor/2;
// Larghezza sperimentale totale FWHM come se fosse una Voigt

double inst=atof(OKBottomDlg->Edit16->Text.c_str())/5000.*wave;
  lor=fabs(wtot-pow(inst,2)/wtot);
 //Larghezza totale in Angstrom epurata dalla larghezza strumentale

// lor*=pow(aut,1.152);
  //Larghezza lorentziana in Angstrom corretta per l'autoassorbimento



 // Inizio Calcolo Densità

 float perc;
   double zi= zZ(Form9->Edit3->Text.c_str(),1,atof(Form9->Edit7->Text.c_str()));
   double zii= zZ(Form9->Edit3->Text.c_str(),2,atof(Form9->Edit7->Text.c_str()));


 for (int w=0; w <=Form9->StringGrid2->RowCount; w++)
 {
 if (Form9->StringGrid2->Cells[1][w]== Trim(Form9->Edit3->Text))
 {
 perc=atof(Form9->StringGrid2->Cells[2][w].c_str());
 break;
 }
 }

sprintf(sqls,"SELECT Ei FROM %s WHERE ion=%i AND [wavelen] BETWEEN %f AND %f",Form9->Edit3->Text.c_str(),ioniz,wave-0.04,wave+0.04);
Form9->Query7->SQL->Clear();
Form9->Query7->SQL->Add(sqls);
Form9->Query7->Open();
Form9->Query7->First();

  float Ei=Form9->Query7->FieldByName("Ei")->AsFloat;

 double nq;
  switch(ioniz)
  {
  case 1:
  nq=denel/(denel+4.8E15*pow(tmp,1.5)*exp(-1.44*Eio/tmp)*zii/zi)*gi*exp(-1.44*Ei/tmp)/zi;
   break;
  case 2:
   nq=(1.0-denel/(denel+4.8e15*pow(tmp,1.5)*exp(-1.44*Eio/tmp)*zii/zi))*gi*exp(-1.44*Ei/tmp)/zii;
  break;
  }
double Nl=nq*atof(Form21->Edit14->Text.c_str())*perc/100.0;

 // Fine Calcolo Densità

double pi=3.1415;
double sl2=0.832554611;
// double a=lor/gau*0.832;
// double b=3.1415*3.6E18*gau/pow(wave,2);
// double f=fabs(aki)*1.5E-8*pow(wave,2)*gk/gi;
// double k0=9E-2*Nl*f/b;
// double l=wave-20.0;
// double integ=0.0;
// double inte0=0.0;
double lu=atof(Form21->Edit13->Text.c_str());
/* double knu,tt,X;
for (int jj=0;jj<=200;jj++)
{
l+=39.9/200.0;
/*
X=1.66/gau*(l-pow(l,2)/wave);
knu=0.0;
for (int t=0;t<=200;t++)
{
tt=10.0/200.0*t-5;
knu+=10.0/200.0*exp(-pow(tt,2))/(pow(tt-X,2)+pow(a,2));
}
knu=1.77/(pow(X,2)+pow(a,2));
knu*=(k0*a/3.14);

double knu=9E-2*Nl*fabs(aki)*1.5E-8*pow(wave,4)*gk/gi/(pow(pi,1.5)*3.6E18)*(lor/sl2)/(4.*pow(l-wave,2)+pow(lor,2));

integ+=(1.0-exp(-knu*lu))/pow(l,2);
inte0+=knu*lu/pow(l,2);
}
double ratt=integ/inte0;
*/
knu0=9E-2*Nl*fabs(aki)*1.5E-8*pow(wave,4)*gk/gi/(pow(pi,1.5)*3.6E18)*(1/sl2)/lor*lu;
float ssa=rtbis(fun,1.e-10,1.,1.e-7);
double ratt=pow(ssa,0.46);
//double ratt=pow((1.0-exp(-knu0*lu))/(knu0*lu),0.46);

Form23->StringGrid1->Cells[3][progre]=FormatFloat("#0.0000",ratt);
 Form23->StringGrid1->Cells[4][progre]=FormatFloat("#0.0000",lor);
  Form23->StringGrid1->Cells[5][progre]=FormatFloat("#0.0000",lor*pow(ssa,0.54));
Form9->Query3->Next();
 }
 
 Form9->Query1->Next();
 }
  Form23->StringGrid1->Refresh();
}
}
//---------------------------------------------------------------------------

double fun(double x)
{
   return (1-knu0*pow(x,0.46)-exp(-knu0*pow(x,-0.54)));
}
//---------------------------------------------------------------------------

