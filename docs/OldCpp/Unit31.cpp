//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop
#include <fstream.h>
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
#include "Unit31.h"
#include "Unit9.h"
static int counter;
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm31 *Form31;
//---------------------------------------------------------------------------
__fastcall TForm31::TForm31(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm31::FormShow(TObject *Sender)
{
if (Form31->Button3->Caption=="DISABLED") {

 Form31->Width=200;
 Form31->StringGrid1->RowCount=Form9->StringGrid2->RowCount;

int I,J;
 for (I = 1; I < Form31->StringGrid1->ColCount; I++)
	for (J = 1; J < Form9->StringGrid2->RowCount; J++)
	 { Form31->StringGrid1->ColWidths[0]=10;
Form31->StringGrid1->ColWidths[1]=40;
Form31->StringGrid1->ColWidths[2]=50;
Form31->StringGrid1->ColWidths[3]=50;
Form31->StringGrid1->Cells[1][0]="Elem";
  Form31->StringGrid1->Cells[2][0]="Conc.";
  Form31->StringGrid1->Cells[3][0]="Ref.";
  Form31->StringGrid1->Cells[1][J] = Form9->StringGrid2->Cells[1][J];
  Form31->StringGrid1->Cells[2][J] = Form9->StringGrid2->Cells[3][J];
  Form31->StringGrid1->Cells[3][J] = "";
  if (Form9->StringGrid2->Cells[1][J]==""){
   Form31->StringGrid1->RowCount=J;
  break;}
  }
	 }
}
//---------------------------------------------------------------------------



void __fastcall TForm31::Exit1Click(TObject *Sender)
{
Form31->Close();
}
//---------------------------------------------------------------------------



void __fastcall TForm31::Button4Click(TObject *Sender)
{
Form31->Close();
}
//---------------------------------------------------------------------------



void __fastcall TForm31::SaveOPC1Click(TObject *Sender)
{
Form31->SaveDialog1->Title="Save STD";
Form31->SaveDialog1->Filter="Standard Data|*.STD";
Form31->SaveDialog1->FileName = "*.STD";
Form31->SaveDialog1->InitialDir=ExtractFilePath(Application->ExeName)+"Templates";
char stringa[80]="The file already exists. Overwrite?";
if (Form31->SaveDialog1->Execute())
		{
		if (FileExists(Form31->SaveDialog1->FileName))
				{
				if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo <<
			mbCancel, 0) != IDYES)
			return;
		}

FILE *out1;
out1 = fopen(AnsiString(Form31->SaveDialog1->FileName).c_str(), "w");
int j=1;
int reco=Form31->StringGrid1->RowCount;
for (j;j < reco;j++)
	 fprintf(out1,"%s %s \n",AnsiString(Form31->StringGrid1->Cells[1][j].c_str()),
	 AnsiString(Form31->StringGrid1->Cells[3][j].c_str()));
			   fclose(out1); }
		}

void __fastcall TForm31::LoadOPC1Click(TObject *Sender)
{
  Form31->OpenDialog1->Title="Load STD";
 Form31->OpenDialog1->Filter = "Standard Data|*.STD";
 Form31->OpenDialog1->FileName = "*.STD";
 Form31->OpenDialog1->InitialDir=ExtractFilePath(Application->ExeName);
  if (Form31->OpenDialog1->Execute())
  {
	int handle;

   FILE *out2;
   AnsiString fn= Form31->OpenDialog1->FileName;
   handle = open(fn.c_str(),S_IREAD);
   /* now turn the handle into a stream */
   out2 = fdopen(handle,"rt");

   if (out2 == NULL)
	 ShowMessage("Open failed");
   else
   {
   char a1[32],a2[32],a3[32];
	int i;
	for (i = 1; i < Form31->StringGrid1->RowCount; i++) {
	 fscanf(out2, "%s %s \n",a1,a3);
	 if (Form31->StringGrid1->Cells[1][i]==a1) {
		Form31->StringGrid1->Cells[3][i]=a3;
		}
		else {
		  ShowMessage("WARNING!: Standard mismatch");
        }

	}
   }
 }

}
//---------------------------------------------------------------------------

void __fastcall TForm31::Button3Click(TObject *Sender)
{
if (Form31->Button3->Caption=="DISABLED") {
   Form31->Button3->Caption="ENABLED";
}
else Form31->Button3->Caption="DISABLED";
}
//---------------------------------------------------------------------------

