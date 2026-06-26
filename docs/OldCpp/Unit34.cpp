//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop

#include "Unit34.h"
#include "SDIMain.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm34 *Form34;
//---------------------------------------------------------------------------
__fastcall TForm34::TForm34(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm34::Button1Click(TObject *Sender)
{
AnsiString as;
   as = ChangeFileExt(SDIAppForm->SaveDialog1->FileName,".bff");
SDIAppForm->SaveDialog1->Title="Save Batch Fit";
SDIAppForm->SaveDialog1->Filter = "Batch Fit File|*.bff";
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

Form34->Memo1->Lines->SaveToFile(SDIAppForm->SaveDialog1->FileName);

}
}
//---------------------------------------------------------------------------

void __fastcall TForm34::Button2Click(TObject *Sender)
{
Form34->Close();
}
//---------------------------------------------------------------------------

