//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include <stdio.h>
#include "SDIMain.h"
#include "Unit1.h"
#include "Unit6.h"
#include "Unit5.h"
#include "Unit7.h"
#include <math.h>
#define COLORE 12632150

//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm5 *Form5;
//---------------------------------------------------------------------------
__fastcall TForm5::TForm5(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm5::DBGrid1DblClick(TObject *Sender)
{
char lab[300];

   float range=atof(AnsiString(OKBottomDlg->Edit9->Text).c_str());
    float freq;

   freq = Form5->Query1->FieldByName("wavelen")->AsFloat;

int ioniz=Form5->Query1->FieldValues["ion"];

AnsiString sp = Form5->Query1->FieldValues["specie"];
int lg = StrLen(sp.c_str());
if (sp.SubString(lg,1)=="+")
{
sp=sp.SubString(1,lg-1);
}





  Form6->Edit1->Text=sp;
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",AnsiString(Form6->Edit1->Text).c_str());
   break;
  case 2:
   sprintf(lab,"%s II",AnsiString(Form6->Edit1->Text).c_str());
  break;
  }
Form6->Show();

char sqls[300];
  Form6->Table1->First();
 float diffe=10000.0;
  int indx=0;
    int e;
 for (e=0; e < Form6->Table1->RecordCount; e++)
 {
 if (fabs(freq - Form6->Table1->FieldByName("wavelen")->AsFloat) < diffe)
 {
 diffe=fabs(freq - Form6->Table1->FieldByName("wavelen")->AsFloat);
  indx=e;
 }
 else
        {
        break;
        }
 Form6->Table1->Next();
 }
  Form6->Table1->RecNo=indx+1;
  Form6->Table1->Edit();
 Form5->Edit1->Text=  Form5->Query1->FieldValues["wavelen"];
   Form5->Edit2->Text=  Form5->Query1->FieldValues["specie"];
   Form5->Edit3->Text=  Form5->Query1->FieldValues["ion"];
 sprintf(sqls,"SELECT * FROM %s where wavelen>(%s - 0.04) and wavelen < (%s + 0.04) and ion=%s", sp.c_str(),AnsiString(Form5->Edit1->Text).c_str(),AnsiString(Form5->Edit1->Text).c_str(),AnsiString(Form5->Edit3->Text).c_str());
  Form5->Query2->SQL->Clear();
 Form5->Query2->SQL->Add(sqls);
  Form5->Query2->Open();
Form6->Table1->FieldValues["specie"]=sp;
Form6->Table1->FieldValues["ion"]=Form5->Query1->FieldValues["ion"];
Form6->Table1->FieldValues["asswavelen"]=Form5->Query1->FieldValues["wavelen"];
Form6->Table1->FieldValues["Ek"]=Form5->Query2->FieldValues["Ek"];
Form6->Table1->FieldValues["acc"]=Form5->Query2->FieldValues["acc"];

if (Form6->Table1->FieldValues["Aki"] == -1.0)
{
if (Form5->Query2->FieldByName("Aki")->AsFloat !=0.0)
{
Form6->Table1->FieldValues["Aki"]=-Form5->Query2->FieldByName("Aki")->AsFloat;
}
else
{
Form6->Table1->FieldValues["Aki"]=-1.0;
}
}
else
{
if (Form6->Table1->FieldByName("Aki")->AsFloat >= 0.0)
{
Form6->Table1->FieldValues["Aki"]=Form5->Query2->FieldByName("Aki")->AsFloat;
}
else
{
Form6->Table1->FieldValues["Aki"]=-Form5->Query2->FieldByName("Aki")->AsFloat;
}
}
Form6->Table1->FieldValues["gk"]=Form5->Query2->FieldValues["gk"];
Form6->Table1->FieldValues["gi"]=Form5->Query2->FieldValues["gi"];
Form6->Table1->FieldValues["acc"]=Form5->Query2->FieldValues["acc"];

Form6->Table1->Post();

Form6->Table1->Refresh();



    float soglia=atof(AnsiString(OKBottomDlg->Edit17->Text).c_str());
  if (Form6->Table1->FieldByName("Aki")->AsFloat >= soglia && Form6->Table1->FieldByName("Aki")->AsFloat != 0.0)
  {
    SDIAppForm->Series4->ValueColor[indx]=clYellow;
  }
  else
  {
  SDIAppForm->Series4->ValueColor[indx]=COLORE;
  }
     SDIAppForm->Series4->XLabel[indx]=lab;
  }

//---------------------------------------------------------------------------

void __fastcall TForm5::DBGrid1KeyDown(TObject *Sender, WORD &Key,
      TShiftState Shift)
{
   if (Shift.Contains(ssAlt) && Query1->RecordCount !=0)
 {
  char sqls[300];
 GroupBox1->Visible=true;
 Edit1->Text= Query1->FieldValues["wavelen"];
  Edit2->Text= Query1->FieldValues["specie"];
  Edit3->Text= Query1->FieldValues["ion"];
 sprintf(sqls,"SELECT * FROM %s where wavelen>(%s - 0.04) and wavelen < (%s + 0.04) and ion=%s", AnsiString(Form5->Edit2->Text).c_str(),AnsiString(Form5->Edit1->Text).c_str(),AnsiString(Form5->Edit1->Text).c_str(),AnsiString(Form5->Edit3->Text).c_str());
  Form5->Query2->SQL->Clear();
 Form5->Query2->SQL->Add(sqls);
  Form5->Query2->Open();
}
}
//---------------------------------------------------------------------------



void __fastcall TForm5::DBGrid1KeyUp(TObject *Sender, WORD &Key,
      TShiftState Shift)
{
 GroupBox1->Visible=false;         
}
//---------------------------------------------------------------------------







