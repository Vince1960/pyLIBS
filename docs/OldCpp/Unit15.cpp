//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include "Unit1.h"
#include "Unit6.h"
#include "SDIMain.h"
#include "Unit15.h"
#include <dos.h>
#include <math.h>
#include <dir.h>
#include <stdio.h>
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm15 *Form15;
//---------------------------------------------------------------------------
__fastcall TForm15::TForm15(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------


void __fastcall TForm15::Button1Click(TObject *Sender)
{
Form15->Close();
SDIAppForm->SaveDialog1->Title="Save Template";
AnsiString fn=ExtractFilePath(Application->ExeName)+"Templates";
SDIAppForm->SaveDialog1->Filter = "Templates|*.DB";
 SDIAppForm->SaveDialog1->FileName = "*.DB";
 SDIAppForm->SaveDialog1->InitialDir=ExtractFilePath(Application->ExeName)+"Templates";

if (SDIAppForm->SaveDialog1->Execute())
{
TTable *NewTable = new TTable(Form6);
NewTable->Active=false;
NewTable->TableName=SDIAppForm->SaveDialog1->FileName;


NewTable->TableType = ttParadox;

 char stringa[80]="This will overwrite an existing template. Continue?";


if (FileExists(SDIAppForm->SaveDialog1->FileName))
{
if (MessageDlg(stringa, mtConfirmation, TMsgDlgButtons() << mbYes << mbNo << mbCancel, 0) != IDYES) return;

}

Form6->BatchMove1->Source=Form6->Table1;
    Form6->BatchMove1->Destination=NewTable;
       Form6->BatchMove1->Execute();

 /* scrivo il template info file*/




 /*recupero la versione di LIBS++*/
  AnsiString ver;
 const AnsiString InfoStr[10] = {"CompanyName", "FileDescription", "FileVersion", "InternalName", "LegalCopyright", "LegalTradeMarks", "OriginalFileName", "ProductName", "ProductVersion", "Comments"};
  char *ExeName = AnsiString(Application->ExeName).c_str();
  DWORD n,size=0;
  n = GetFileVersionInfoSize(ExeName, &size);
   char label[10];
	//

   DWORD               dwSize              = 0;
    BYTE                *pbVersionInfo      = NULL;
    VS_FIXEDFILEINFO    *pFileInfo          = NULL;
    UINT                puLenFileInfo       = 0;

    // get the version info for the file requested
	dwSize = GetFileVersionInfoSize( ExeName, NULL );

	if ( dwSize == 0 )
	{
		sprintf(label, "Error in GetFileVersionInfoSize: %d\n", GetLastError() );
		ShowMessage(label);
		return;
	}

    pbVersionInfo = new BYTE[ dwSize ];

	if ( !GetFileVersionInfo( ExeName, 0, dwSize, pbVersionInfo ) )
    {
		sprintf(label, "Error in GetFileVersionInfo: %d\n", GetLastError() );
		delete[] pbVersionInfo;
		ShowMessage(label);
        return;
    }

    if ( !VerQueryValue( pbVersionInfo, TEXT("\\"), (LPVOID*) &pFileInfo, &puLenFileInfo ) )
    {
		sprintf(label, "Error in VerQueryValue: %d\n", GetLastError() );
		ShowMessage(label);
		delete[] pbVersionInfo;
        return;
    }

    // pFileInfo->dwFileVersionMS is usually zero. However, you should check
    // this if your version numbers seem to be wrong

 sprintf(label,"%d.%d.%d.%d\n",
		( pFileInfo->dwFileVersionMS >> 16 ) & 0xff,
		( pFileInfo->dwFileVersionMS >> 8) & 0xff,
		( pFileInfo->dwFileVersionLS >>  16 ) & 0xff,
        ( pFileInfo->dwFileVersionLS >>  8 ) & 0xff
        );

    // pFileInfo->dwProductVersionMS is usually zero. However, you should check
    // this if your version numbers seem to be wrong

 /*	sprintf(label,"%d.%d.%d.%d\n",
		( pFileInfo->dwProductVersionMS >> 24 ) & 0xff,
		( pFileInfo->dwProductVersionMS >> 16 ) & 0xff,
		( pFileInfo->dwProductVersionMS >>  8 ) & 0xff,
		( pFileInfo->dwProductVersionMS >>  0 ) & 0xff
        );
 */
 /*
  if (n > 0)
  {
   // char *pBuf = (char *) malloc(n);
   int ver;
   ver=GetFileVersion(ExeName);

  //	  DWORD *pValue;
  //    unsigned int Len;
 //	  AnsiString temp = "StringFileInfo\\041004E4\\ProductVersion";

if (VerQueryValue(pBuf, temp.c_str(), (LPVOID *)&pValue, &Len))

		{
		ver = StrPas(PChar(pValue));
		}
	free(pBuf);

  }
 */
 /* trovo la data*/

 struct date d;

   getdate(&d);
   char date[15];
   sprintf(date,"%d/%d/%d", d.da_day, d.da_mon, d.da_year);



 /*comincio a scrivere il file di correzione*/
        FILE *out;

	     AnsiString as;
   as = ChangeFileExt(SDIAppForm->SaveDialog1->FileName,".cor");
	out = fopen(as.c_str(), "wt");

		if (OKBottomDlg->CheckBox2->Checked)
		fprintf(out,"Global Correction: %s\n",AnsiString(OKBottomDlg->Edit10->Text.c_str()));
		else
		fprintf(out,"Global Correction: NO\n");

  /*      if (OKBottomDlg->CheckBox1->Checked)
		fprintf(out,"Single File Correction: %s\n",AnsiString(OKBottomDlg->Edit11->Text.c_str()));
		else
		fprintf(out,"Single File Correction: NO\n");
  */

        if (OKBottomDlg->RadioButton1->Checked)
		fprintf(out,"Correction before integral calculation\n");
        else
		fprintf(out,"Correction after integral calculation\n");

		if (strcmp(AnsiString(SDIAppForm->Edit9->Text).c_str(),"")!=0) fprintf(out,"Spectrum Filename: %s\n",AnsiString(ExtractFileName(SDIAppForm->Edit9->Text).c_str()));
		else fprintf(out,"Spectrum Filename: none\n");

		if (strcmp(AnsiString(OKBottomDlg->Edit13->Text).c_str(),"")!=0) fprintf(out,"User: %s\n", AnsiString(OKBottomDlg->Edit13->Text.c_str()));
		else fprintf(out,"User: none\n");

		fprintf(out,"Version: %s\n", label);
		fprintf(out,"Created Date: %s\n", date);
		fprintf(out,"Notes: %s\n", AnsiString(Form15->Memo1->Lines->Text.c_str()));
		fclose(out);

        ShowMessage(IntToStr(Form6->BatchMove1->MovedCount) + " records copied");
}
SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
}
//---------------------------------------------------------------------------
