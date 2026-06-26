//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop
#include <dos.h>
#include <stdio.h>
#include "Unit33.h"
#include "SDIMain.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"

TForm33 *Form33;
//---------------------------------------------------------------------------
__fastcall TForm33::TForm33(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm33::Button2Click(TObject *Sender)
{
Form33->Close();
}
//---------------------------------------------------------------------------

void __fastcall TForm33::Button1Click(TObject *Sender)
{
AnsiString as;
   as = ChangeFileExt(SDIAppForm->SaveDialog1->FileName,".frf");
SDIAppForm->SaveDialog1->Title="Save Fit Report";
SDIAppForm->SaveDialog1->Filter = "Fit Report|*.frf";
 SDIAppForm->SaveDialog1->FileName = as;

if (SDIAppForm->SaveDialog1->Execute())
{
if (FileExists(SDIAppForm->SaveDialog1->FileName))
		{
		char stringa[80]="The file already exists. Overwrite?";
			if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
				mbCancel, 0) != IDYES)
                              {
				return;
                                  }
                              else
                             {
								 DeleteFile(SDIAppForm->SaveDialog1->FileName);
                              }
		}

Form33->Memo1->Lines->SaveToFile(SDIAppForm->SaveDialog1->FileName);

}

}
//---------------------------------------------------------------------------

void __fastcall TForm33::Button3Click(TObject *Sender)
{
Form33->Memo1->Text="";

}
//---------------------------------------------------------------------------

