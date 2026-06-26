//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include "Unit23.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm23 *Form23;
//---------------------------------------------------------------------------
__fastcall TForm23::TForm23(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------


void __fastcall TForm23::Button2Click(TObject *Sender)
{
for (int w=1; w<=Form23->StringGrid1->RowCount;w++)
{
Form23->StringGrid1->Cells[3][w]="";
}
Form23->Hide();
}
//---------------------------------------------------------------------------

void __fastcall TForm23::Button1Click(TObject *Sender)
{
// Form23->Hide();
void calcola();
calcola();      
}
//---------------------------------------------------------------------------


