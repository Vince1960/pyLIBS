//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop
#include <vcl.h>
#include <string.h>
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
#include <math.h>
#include <sysdefs.h>
#include <dstring.h>
#include <Clipbrd.hpp>
#include <vector.h>
#include <dos.h>
#include "Unit1.h"
#include "Unit6.h"
#include "Unit13.h"
#include "Unit14.h"
#include "Unit15.h"
#include "Unit16.h"
#include "Unit33.h"
#include "Unit34.h"
#include "Unit35.h"
#include "SDIMain.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm35 *Form35;
//---------------------------------------------------------------------------
__fastcall TForm35::TForm35(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm35::Button2Click(TObject *Sender)
{
AnsiString as;
   as = ChangeFileExt(SDIAppForm->SaveDialog1->FileName,".fls");
SDIAppForm->SaveDialog1->Title="Save File List";
SDIAppForm->SaveDialog1->Filter = "File List|*.fls";
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

Form35->Memo1->Lines->SaveToFile(SDIAppForm->SaveDialog1->FileName);

}
}
//---------------------------------------------------------------------------

void __fastcall TForm35::Button1Click(TObject *Sender)
{

  SDIAppForm->OpenDialog->FileName = "";
	 SDIAppForm->OpenDialog->Filter = "Avantes Binary Files (*.roh)|*.roh|Avantes Files (*.trt)|*.trt|All Files (*.*)|*.*";
	AnsiString fp;
	 SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
	if (SDIAppForm->OpenDialog->Execute())
  {
int st, stp;
  switch(Form35->RadioGroup1->ItemIndex)
  {
  case 0:
   st=0;
   stp=1;
   break;
  case 1:
	st=0;
   stp=2;
  break;
  case 2:
   st=1;
   stp=2;
  break;
  }

  for (int I = st; I < SDIAppForm->OpenDialog->Files->Count; I+=stp)
	{
  Form35->Memo1->Lines->Append(AnsiString(SDIAppForm->OpenDialog->Files->Strings[I]).c_str());
	}
	}

}
//---------------------------------------------------------------------------

void __fastcall TForm35::Button3Click(TObject *Sender)
{
Form35->Close();
}
//---------------------------------------------------------------------------

void __fastcall TForm35::Button4Click(TObject *Sender)
{
 void openfile(AnsiString nomefile);
void compfile(AnsiString nomefile);
   void calcolh();
	struct date d;
	 getdate(&d);


   if (CheckBox1->Checked) {

    char date[15];
   sprintf(date,"%d/%d/%d", d.da_day, d.da_mon, d.da_year);
	Form34->Show();
  Form34->Memo1->Text=date;


	  Form34->Memo1->Lines->Append("Filename Species Ion Wav. Inte wg wl");

   Form34->ProgressBar1->Position=0;

	for (int I = 0; I < Form35->Memo1->Lines->Count; I ++)
	{

	 for (int y=1;y<Form13->StringGrid1->RowCount;y++)
	 {
	 if (Form13->StringGrid1->Cells[1][y]=="")
	{
	Form13->StringGrid1->Cells[1][y]=AnsiString(Form35->Memo1->Lines->Strings[I].c_str());

	Form13->StringGrid1->Refresh();
	break;
	}
	  }

	  Form34->Show();
	   Form34->Refresh();
	   void condizioni();
Form14->Width=210;
Form14->Show();
Form14->Width=Form14->Panel2->Width;
condizioni();
Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
Form6->Table1->RecNo=1;

 for (int q=1; q < Form6->Table1->RecordCount+1; q++) {
 Form6->Table1->RecNo=q;
Form6->Table1->Edit();
Form6->Table1->FieldValues["fitwavelen"]=0.0;
Form6->Table1->FieldValues["inte"]=0.0;
Form6->Table1->FieldValues["wg"]=0.0;
Form6->Table1->FieldValues["wl"]=0.0;
 }


 // ------------- Compare File

	compfile(AnsiString(Form35->Memo1->Lines->Strings[I].c_str()));

  // -------------- Swap File

	void swap();
		 swap();

   // ------------- Fit

   SDIAppForm->AutofitClick(Sender);


   char s1[1000],s2[1000];


	  Form6->Table1->First();

	sprintf(s1,"%s",AnsiString(Form35->Memo1->Lines->Strings[I].c_str()));
	for (int iz=0; iz < Form6->Table1->RecordCount; iz++) {
   AnsiString qel;
   Form6->Table1->RecNo=iz+1;
   qel=Form6->Table1->FieldByName("specie")->AsString;
   int qion=int(Form6->Table1->FieldByName("ion")->AsFloat);
   float qwav=Form6->Table1->FieldByName("asswavelen")->AsFloat;
   float qinte=Form6->Table1->FieldByName("inte")->AsFloat;
   float qwg=Form6->Table1->FieldByName("wg")->AsFloat;
   float qwl=Form6->Table1->FieldByName("wl")->AsFloat;
   sprintf(s2,"%s %s %i %4.2f %4.2f %4.2f %4.2f",s1,qel,qion,qwav,qinte,qwg,qwl);
   sprintf(s1,"%s",s2);
   }
	Form34->Memo1->Lines->Append(s1);
	Form34->ProgressBar1->Position= (I*100)/(Form35->Memo1->Lines->Count);
	 SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;

  // --------------- Delete File after fitting


	 Form13->Edit1->Text=Form13->StringGrid1->Cells[1][1];
	 Form13->StringGrid1->Row=1;

   void deleteseries();
deleteseries();
	 }
  Form34->Memo1->Lines->Append("End Batch Fit");
}
// AutoFit full spectrum
else {
	for (int I = 0; I < Form35->Memo1->Lines->Count; I ++)
	{
		 for (int y=1;y<Form13->StringGrid1->RowCount;y++)
	 {
	 if (Form13->StringGrid1->Cells[1][y]=="")
	{
	Form13->StringGrid1->Cells[1][y]=AnsiString(Form35->Memo1->Lines->Strings[I].c_str());

	Form13->StringGrid1->Refresh();
	break;
	}
	  }
	  Form6->Table1->Active=true;
SDIAppForm->Series4->Active=true;
Form6->Table1->RecNo=1;

 for (int q=1; q < Form6->Table1->RecordCount+1; q++) {
 Form6->Table1->RecNo=q;
Form6->Table1->Edit();
Form6->Table1->FieldValues["fitwavelen"]=0.0;
Form6->Table1->FieldValues["inte"]=0.0;
Form6->Table1->FieldValues["wg"]=0.0;
Form6->Table1->FieldValues["wl"]=0.0;
 }
 // ------------- Compare File

 compfile(AnsiString(Form35->Memo1->Lines->Strings[I].c_str()));

  // -------------- Swap File

	void swap();
		 swap();
// ------------- Fit
   SDIAppForm->AutofitClick(Sender);

 // ------------- Calculate ne

int sc=SDIAppForm->Chart1->SeriesCount();

   calcolh();

	  SDIAppForm->Series3->Clear();

   if ( SDIAppForm->Chart1->SeriesCount() > sc)
   {
   int sma=SDIAppForm->Chart1->SeriesCount();
   for (int su=sma-1; su > sc-1 ;su--)
   {
   SDIAppForm->Chart1->Series[su]->Free();
   }
   }

	SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;

 AnsiString nnn= FormatFloat("0.00E+00",atof(AnsiString(Form16->Edit1->Text).c_str())*1.e17);
  AnsiString wwg= FormatFloat("0.00",atof(AnsiString(Form16->Edit2->Text).c_str()));
   AnsiString wwl= FormatFloat("0.00",atof(AnsiString(Form16->Edit3->Text).c_str()));
   AnsiString dele="Electron Density: "+nnn+" cm-3";
	AnsiString laga="Gaussian width: "+wwg+" Angstrom";
	 AnsiString lalo="Lorentzian width: "+wwl+" Angstrom";

// ------------- Save Template
 AnsiString pat=ExtractFilePath(Application->ExeName)+"Templates";
  TTable *NewTable = new TTable(Form6);
   NewTable->Active=false;
  AnsiString dbnom=ExtractFileName(ChangeFileExt(Form35->Memo1->Lines->Strings[I],".DB"));
	AnsiString infonom=ExtractFileName(ChangeFileExt(AnsiString(Form35->Memo1->Lines->Strings[I].c_str()),".cor"));
	AnsiString dbnome=pat+"\\"+dbnom;
	 AnsiString infonome=pat+"\\"+infonom;
	NewTable->TableName=dbnome;
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

 /* trovo la data*/

 struct date d;

   getdate(&d);
   char date[15];
   sprintf(date,"%d/%d/%d", d.da_day, d.da_mon, d.da_year);



 /*comincio a scrivere il file di correzione*/
        FILE *out;

	     AnsiString as;
   as = infonome;
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
		fprintf(out,"%s\n%s\n%s\n", dele,laga,lalo);
		fclose(out);

NewTable->TableType = ttParadox;


// --------------- Delete File after fitting


	 Form13->Edit1->Text=Form13->StringGrid1->Cells[1][1];
	 Form13->StringGrid1->Row=1;
 //	 Form6->Show();

   void deleteseries();
deleteseries();
	}
 Form34->Memo1->Lines->Append("End Batch Fit");
}

}
//---------------------------------------------------------------------------

void __fastcall TForm35::Button6Click(TObject *Sender)
{
Form35->Memo1->Clear();
}
//---------------------------------------------------------------------------

void __fastcall TForm35::Button5Click(TObject *Sender)
{
 FILE *in;
 SDIAppForm->OpenDialog1->Title="Load File List";
 SDIAppForm->OpenDialog1->Filter = "List|*.fls";
 SDIAppForm->OpenDialog1->FileName = "*.fls";

  if (SDIAppForm->OpenDialog1->Execute())
  {
	char buf[200]="";
 in = fopen(AnsiString(SDIAppForm->OpenDialog1->FileName).c_str(),"rt");

 ag:

   if (fscanf(in,"%s", &buf)!=EOF) {
		Form35->Memo1->Lines->Append(buf);
		goto ag;
   }

fclose(in);
   }
}
//---------------------------------------------------------------------------

void __fastcall TForm35::LoadList1Click(TObject *Sender)
{
Form35->Button5Click(Sender);
}
//---------------------------------------------------------------------------

void __fastcall TForm35::ClearList1Click(TObject *Sender)
{
Form35->Button6Click(Sender);
}
//---------------------------------------------------------------------------

void __fastcall TForm35::SaveList1Click(TObject *Sender)
{
Form35->Button2Click(Sender);
}
//---------------------------------------------------------------------------
void __fastcall TForm35::CheckBox2MouseUp(TObject *Sender, TMouseButton Button, TShiftState Shift,
		  int X, int Y)
{
 CheckBox1->Checked=False;
  CheckBox2->Checked=True;
}
//---------------------------------------------------------------------------

void __fastcall TForm35::CheckBox1MouseUp(TObject *Sender, TMouseButton Button, TShiftState Shift,
          int X, int Y)
{
  CheckBox1->Checked=True;
  CheckBox2->Checked=False;
}
//---------------------------------------------------------------------------



void __fastcall TForm35::Button7Click(TObject *Sender)
{
void openfile(AnsiString nomefile);
void calcolh();
         struct date d;
	 getdate(&d);
    char date[15];
   sprintf(date,"%d/%d/%d", d.da_day, d.da_mon, d.da_year);
	Form34->Show();
  Form34->Memo1->Text=date;


	  Form34->Memo1->Lines->Append("Filename                            ne        Gaussian width   Lorentzian Width");

	 AnsiString s1;

 for (int I = 0; I < Form35->Memo1->Lines->Count; I ++)
	{
		openfile(AnsiString(Form35->Memo1->Lines->Strings[I].c_str()));


   calcolh();

	SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;
  s1=AnsiString(Form35->Memo1->Lines->Strings[I]);
 AnsiString nnn= FormatFloat("0.00E+00",atof(AnsiString(Form16->Edit1->Text).c_str())*1.e17);
  AnsiString wwg= FormatFloat("0.00",atof(AnsiString(Form16->Edit2->Text).c_str()));
   AnsiString wwl= FormatFloat("0.00",atof(AnsiString(Form16->Edit3->Text).c_str()));
	 AnsiString tt=s1+"    "+ nnn + "   " + wwg + "     " + wwl;
  Form34->Memo1->Lines->Append(tt);
  Form34->ProgressBar1->Position= (I*100)/(Form35->Memo1->Lines->Count);
//   void deleteseries();
// deleteseries();
for (int j=0;j<6;j++)
{
SDIAppForm->Chart1->Series[j]->Clear();
}

  int sc=SDIAppForm->Chart1->SeriesCount();
  if(SDIAppForm->Chart1->SeriesCount()>6)
  {
  for (int u=6; u < sc;u++)
  {
   SDIAppForm->Chart1->Series[6]->Free();
  }
  }
	 SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;

  // --------------- Delete File after fitting


	 Form13->Edit1->Text=Form13->StringGrid1->Cells[1][1];
	 Form13->StringGrid1->Row=1;

	 }
  Form34->Memo1->Lines->Append("End Batch Fit");
}
//---------------------------------------------------------------------------


void __fastcall TForm35::Button8Click(TObject *Sender)
{
void openfile(AnsiString nomefile);
         struct date d;
	 getdate(&d);
    char date[15];
   sprintf(date,"%d/%d/%d", d.da_day, d.da_mon, d.da_year);
	Form34->Show();
  Form34->Memo1->Text=date;


	  Form34->Memo1->Lines->Append("Filename                                                Total Intensity");

	 AnsiString s1;

 for (int I = 0; I < Form35->Memo1->Lines->Count; I ++)
	{
		openfile(AnsiString(Form35->Memo1->Lines->Strings[I].c_str()));

	SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;

	 float totint=0.0;

  for (int w=SDIAppForm->Series1->FirstValueIndex;w<SDIAppForm->Series1->LastValueIndex+1;w++)
	  {
	   totint+=SDIAppForm->Series1->YValues->Value[w];
	   }

  s1=AnsiString(Form35->Memo1->Lines->Strings[I]);
 AnsiString nnn= FormatFloat("0.00E+00",totint);

	 AnsiString tt=s1+"    "+ nnn;
  Form34->Memo1->Lines->Append(tt);
  Form34->ProgressBar1->Position= (I*100)/(Form35->Memo1->Lines->Count);
}
}
//---------------------------------------------------------------------------

