//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include "SDIMain.h"
#include "Unit16.h"
#include "Unit9.h"
#include "Unit27.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm16 *Form16;
//---------------------------------------------------------------------------
__fastcall TForm16::TForm16(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm16::Button1Click(TObject *Sender)
{
                Close();
}
//---------------------------------------------------------------------------

void __fastcall TForm16::Button2Click(TObject *Sender)
{
Form9->Edit2->Text=FormatFloat("0.00E+00",atof(Form16->Edit1->Text.c_str())*1e17);
Form9->RadioGroup2->ItemIndex=2;
Form27->Edit8->Text=FormatFloat("0.00E+00",atof(Form16->Edit1->Text.c_str())*1e17);
Close();
}
//---------------------------------------------------------------------------
void __fastcall TForm16::Button3Click(TObject *Sender)
{
SDIAppForm->Edit7->Text="-1";

Close();
}
//---------------------------------------------------------------------------

