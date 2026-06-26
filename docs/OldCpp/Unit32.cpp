//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop

#include "Unit31.h"
#include "Unit32.h"
static int counter;
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm32 *Form32;
//---------------------------------------------------------------------------
__fastcall TForm32::TForm32(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm32::Button2Click(TObject *Sender)
{
int J=counter++;
   Form31->StringGrid1->Cells[3][J]=Form32->Edit1->Text;
}
//---------------------------------------------------------------------------
void __fastcall TForm32::FormShow(TObject *Sender)
{
int J;
J= counter;
Form32->Label2->Caption = Form31->StringGrid1->Cells[1][J];

}
//---------------------------------------------------------------------------
													 ;