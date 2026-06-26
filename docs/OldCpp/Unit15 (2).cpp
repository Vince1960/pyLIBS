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

if (FileExists(SDIAppForm->SaveDialog1->FileName))
{
if (Application->MessageBox((AnsiString("Overwrite table\?")).c_str(),"Table Exists", MB_YESNO) == IDNO)
 {
 return;
 }
}

Form6->BatchMove1->Source=Form6->Table1;
    Form6->BatchMove1->Destination=NewTable;
       Form6->BatchMove1->Execute();

 /* scrivo il template info file*/


   AnsiString as;
   as = ChangeFileExt(SDIAppForm->SaveDialog1->FileName,".cor");

 /*recupero la versione di LIBS++*/
  AnsiString ver;
 const AnsiString InfoStr[10] = {"CompanyName", "FileDescription", "FileVersion", "InternalName", "LegalCopyright", "LegalTradeMarks", "OriginalFileName", "ProductName", "ProductVersion", "Comments"};
  char *ExeName = Application->ExeName.c_str();
  DWORD n,size=0;
  n = GetFileVersionInfoSize(ExeName, &size);

  if (n > 0)
  {
    char *pBuf = (char *) malloc(n);
    GetFileVersionInfo(ExeName, 0, n, pBuf);
 
      DWORD *pValue;
      unsigned int Len;
      AnsiString temp = "StringFileInfo\\041004E4\\ProductVersion";
  if (VerQueryValue(pBuf, temp.c_str(), (LPVOID *)&pValue, &Len))

        {
        ver = StrPas(PChar(pValue));
        }
    free(pBuf);
  }

 /* trovo la data*/

 struct date d;

   getdate(&d);

   char date[15];
   sprintf(date,"%d/%d/%d", d.da_day, d.da_mon, d.da_year);



 /*comincio a scrivere il file di correzione*/
        FILE *out;

        out = fopen(as.c_str(), "wt");

        if (OKBottomDlg->CheckBox2->Checked)
        fprintf(out,"Global Correction: %s",OKBottomDlg->Edit10->Text.c_str());
        else
        fprintf(out,"Global Correction: NO");

        if (OKBottomDlg->CheckBox1->Checked)
        fprintf(out,"\nSingle File Correction: %s",OKBottomDlg->Edit11->Text.c_str());
        else
        fprintf(out,"\nSingle File Correction: NO");

        if (OKBottomDlg->RadioButton1->Checked)
        fprintf(out,"\nCorrection before integral calculation");
        else
        fprintf(out,"\nCorrection after integral calculation");

        if (strcmp(SDIAppForm->Edit9->Text.c_str(),"")!=0) fprintf(out,"\nSpectrum Filename: %s",ExtractFileName(SDIAppForm->Edit9->Text.c_str()));
        else fprintf(out,"\nSpectrum Filename: none");

        if (strcmp(OKBottomDlg->Edit13->Text.c_str(),"")!=0) fprintf(out,"\nUser: %s", OKBottomDlg->Edit13->Text.c_str());
        else fprintf(out,"\nUser: none");
        
        fprintf(out,"\nVersion: %s", ver);
        fprintf(out,"\nCreated Date: %s", date);
        fprintf(out,"\nNotes: %s", Form15->Memo1->Lines->Text);
        fclose(out);

        ShowMessage(IntToStr(Form6->BatchMove1->MovedCount) + " records copied");
}
SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
}
//---------------------------------------------------------------------------
