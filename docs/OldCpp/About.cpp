//---------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include "SDIMain.h"
#include "About.h"
//--------------------------------------------------------------------- 
#pragma resource "*.dfm"
TAboutBox *AboutBox;
//--------------------------------------------------------------------- 
__fastcall TAboutBox::TAboutBox(TComponent *Owner)
	: TForm(Owner)
{

}
//---------------------------------------------------------------------

void __fastcall TAboutBox::FormCreate(TObject *Sender)
{
// SDIAppForm->Image1->Visible=false;
}
//---------------------------------------------------------------------------







