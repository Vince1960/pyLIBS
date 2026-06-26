//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include "SDIMain.h"
#include "Unit18.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm18 *Form18;
//---------------------------------------------------------------------------
__fastcall TForm18::TForm18(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm18::FormActivate(TObject *Sender)
{
Form18->Width=SDIAppForm->Width;

Form18->Left=SDIAppForm->Left;
}
//---------------------------------------------------------------------------

