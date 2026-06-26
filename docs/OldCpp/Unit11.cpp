//---------------------------------------------------------------------------
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
#include "SDIMain.h"
#include "Unit6.h"
#include "Unit11.h"
#include "Unit13.h"
#include <vector.h>
#pragma hdrstop
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm11 *Form11;
//---------------------------------------------------------------------------
__fastcall TForm11::TForm11(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm11::Button1Click(TObject *Sender)
{
float shif=atof(AnsiString(Form11->Edit2->Text).c_str())-atof(AnsiString(Form11->Edit1->Text).c_str());
SDIAppForm->Series1->Active=false;
for (int i=0; i < SDIAppForm->Series1->Count(); i++)
{
SDIAppForm->Series1->XValues->Value[i]+=shif;
}
SDIAppForm->Series1->Active=true;

if (CheckBox2->Checked==true)

{
 int sc=SDIAppForm->Chart1->SeriesCount()-5;

 for (int i = 1; i < sc; i++) {

	 AnsiString nm;
  AnsiString cp="";
		 int ru;
 cp.cat_sprintf("s%i",i);

for (int u=0; u < SDIAppForm->Chart1->SeriesCount();u++)
   {
   nm=SDIAppForm->Chart1->Series[u]->Name;
    if (nm == cp)
    {
	ru=u;
    break;
    }
 }

 SDIAppForm->Chart1->Series[ru]->Active=false;
for (int j=0; j < SDIAppForm->Chart1->Series[ru]->Count(); j++)
{
SDIAppForm->Chart1->Series[ru]->XValues->Value[j]+=shif;
}
SDIAppForm->Chart1->Series[ru]->Active=true;

}
}

 if (CheckBox1->Checked==true)
 {

 SDIAppForm->Series4->Active=false;
for (int w=0; w < SDIAppForm->Series4->Count(); w++)
{
SDIAppForm->Series4->XValues->Value[w]+=shif;
}

 SDIAppForm->Series4->Active=true;

 Form6->Table1->Active=true;
Form6->Table1->First();
for (int w=0; w < Form6->Table1->RecordCount; w++)
{
Form6->Table1->Edit();
Form6->Table1->FieldValues["wavelen"]=Form6->Table1->FieldValues["wavelen"]+shif;
if (Form6->Table1->FieldValues["fitwavelen"] !=0)
        {
if (Form6->Table1->FieldValues["fitwavelen"] <0)
        {
        Form6->Table1->FieldValues["fitwavelen"]=Form6->Table1->FieldValues["fitwavelen"]-shif;
        }
        else
        {
        Form6->Table1->FieldValues["fitwavelen"]=Form6->Table1->FieldValues["fitwavelen"]+shif;
        }
        }
Form6->Table1->Post();
 Form6->Table1->Next();
}
}

 Form11->Close();
}
//---------------------------------------------------------------------------
void __fastcall TForm11::Button2Click(TObject *Sender)
{
Form11->Close();        
}
//---------------------------------------------------------------------------


