//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include "Unit4.h"
#include "Unit6.h"
#include "Unit8.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm8 *Form8;
//---------------------------------------------------------------------------
__fastcall TForm8::TForm8(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm8::Button2Click(TObject *Sender)
{
Form8->Close();        
}
//---------------------------------------------------------------------------


void __fastcall TForm8::Button1Click(TObject *Sender)
{
Table1->Active=false;
Table1->TableName = ComboBox1->Text;
if (Application->MessageBox((AnsiString("Delete table\?")).c_str(),"Confirm", MB_YESNO) == IDYES)
{
 Form8->Close();
}
}
//---------------------------------------------------------------------------







