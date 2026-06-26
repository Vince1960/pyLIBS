//---------------------------------------------------------------------
#include <vcl.h>
#include <stdio.h>
#include <fcntl.h>
#include<io.h>
#pragma hdrstop
#include "SDIMain.h"
 #include "Unit1.h"
 #include "Unit10.h"
 #include "Unit12.h"
  #include "Unit13.h"
   #include "Unit9.h"
  #include "Unit6.h"
  #include "Unit14.h"
   #include "Unit27.h"
      #include "Unit21.h"
   #include "Unit18.h"
   #include "Unit5.h"
//---------------------------------------------------------------------
#pragma resource "*.dfm"
TOKBottomDlg *OKBottomDlg;
//---------------------------------------------------------------------
__fastcall TOKBottomDlg::TOKBottomDlg(TComponent* AOwner)
	: TForm(AOwner)
{
}
//---------------------------------------------------------------------

void __fastcall TOKBottomDlg::OKBtnClick(TObject *Sender)
{

        OKBottomDlg->Hide();
}
//---------------------------------------------------------------------------

void __fastcall TOKBottomDlg::CancelBtnClick(TObject *Sender)
{
        OKBottomDlg->Hide();
}
//---------------------------------------------------------------------------

void __fastcall TOKBottomDlg::Button2Click(TObject *Sender)
{
float xf,yf;
OpenDialog1->FileName=Edit10->Text;
if (OpenDialog1->Execute())
{
Edit10->Text=OpenDialog1->FileName;
float xf,yf;

Form10->Series1->Clear();

   FILE *strm;
  strm = fopen(AnsiString(OKBottomDlg->Edit10->Text).c_str(), "rt");
 do
   {
   fscanf(strm,"%g %g", &xf, &yf);
     if ((OKBottomDlg->CheckBox7->Checked==true) & (xf < 1500.0))
  {
    xf=xf*10.0;
  }
   Form10->Series1->AddXY(xf,yf,' ',clBlack);
    }
while(!feof(strm));
   fclose(strm);
   			Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
}
else
{
Form10->Series1->Clear();
   Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
   Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
}
}
//---------------------------------------------------------------------------

void __fastcall TOKBottomDlg::Button1Click(TObject *Sender)
{

AnsiString fn=ExtractFilePath(Application->ExeName)+"libs++.ini";
  FILE *out;
   out = fopen(fn.c_str(), "wt");

   if (strcmp(AnsiString(OKBottomDlg->Edit13->Text).c_str(),"")!=0) fprintf(out,"%s // Username\n", AnsiString(OKBottomDlg->Edit13->Text).c_str());
   else fprintf(out,"none // Username\n");
   fprintf(out,"%s // Limit Low\n", AnsiString(OKBottomDlg->Edit3->Text).c_str());
   fprintf(out,"%s // Limit High\n", AnsiString(OKBottomDlg->Edit4->Text).c_str());
   fprintf(out,"%s // Ha Lines\n", AnsiString(OKBottomDlg->Edit1->Text).c_str());
   fprintf(out,"%s // Ha Range\n", AnsiString(OKBottomDlg->Edit2->Text).c_str());
   fprintf(out,"%s // First wavelength\n", AnsiString(OKBottomDlg->Edit5->Text).c_str());
   fprintf(out,"%s // Second wavelength\n", AnsiString(OKBottomDlg->Edit6->Text).c_str());
   fprintf(out,"%s // First width\n", AnsiString(OKBottomDlg->Edit12->Text).c_str());
   fprintf(out,"%s // Second width\n", AnsiString(OKBottomDlg->Edit24->Text).c_str());
   fprintf(out,"%s // KappaT\n", AnsiString(OKBottomDlg->Edit25->Text).c_str());
	fprintf(out,"%s // Thresh.\n", AnsiString(OKBottomDlg->Edit7->Text).c_str());
   fprintf(out,"%s // Delta min.\n", AnsiString(OKBottomDlg->Edit8->Text).c_str());
   fprintf(out,"%s // Range\n", AnsiString(OKBottomDlg->Edit9->Text).c_str());
	fprintf(out,"%i // Apply normalization\n", OKBottomDlg->CheckBox2->Checked);
    fprintf(out,"%i // Apply before\n", OKBottomDlg->RadioButton1->Checked);
	fprintf(out,"%i // Apply after\n", OKBottomDlg->RadioButton2->Checked);
	 if (strcmp(AnsiString(OKBottomDlg->Edit10->Text).c_str(),"")!=0) fprintf(out,"%s // Normalization\n", AnsiString(OKBottomDlg->Edit10->Text).c_str());
   else fprintf(out,"none // Normalization\n");
   fprintf(out,"%i // Echelle\n", OKBottomDlg->CheckBox9->Checked);
   if (strcmp(AnsiString(OKBottomDlg->Edit11->Text).c_str(),"")!=0) fprintf(out,"%s // Single file\n", AnsiString(OKBottomDlg->Edit11->Text).c_str());
   else fprintf(out,"none // Single file\n");
   fprintf(out,"%s // Instr. width\n", AnsiString(OKBottomDlg->Edit16->Text).c_str());
	   fprintf(out,"%i // Fix wg\n", OKBottomDlg->CheckBox5->Checked);
	fprintf(out,"%s // Fixed wg\n", AnsiString(OKBottomDlg->Edit14->Text).c_str());
		 fprintf(out,"%i // Fix wl\n", OKBottomDlg->CheckBox6->Checked);
   fprintf(out,"%s // Fixed wl\n", AnsiString(OKBottomDlg->Edit15->Text).c_str());
	fprintf(out,"%s // Aki thres.\n", AnsiString(OKBottomDlg->Edit17->Text).c_str());
	fprintf(out,"%s // Ne low\n", AnsiString(OKBottomDlg->Edit18->Text).c_str());
   fprintf(out,"%s // Ne high\n", AnsiString(OKBottomDlg->Edit19->Text).c_str());
	fprintf(out,"%s // kT low\n", AnsiString(OKBottomDlg->Edit20->Text).c_str());
   fprintf(out,"%s // kT high\n", AnsiString(OKBottomDlg->Edit21->Text).c_str());
      fprintf(out,"%i // Show progress\n", OKBottomDlg->CheckBox3->Checked);
       fprintf(out,"%i // Fix wavel.\n", OKBottomDlg->CheckBox4->Checked);
        fprintf(out,"%i // Convert to A\n", OKBottomDlg->CheckBox7->Checked);
	 fprintf(out,"%s // Iterations\n", AnsiString(OKBottomDlg->Edit22->Text).c_str());
    fprintf(out,"%i // Auto Offset\n", OKBottomDlg->CheckBox8->Checked);
	fprintf(out,"%s // Auto Shift\n", AnsiString(OKBottomDlg->Edit23->Text).c_str());
    fprintf(out,"%i %i %i %i // Main\n", SDIAppForm->Top,SDIAppForm->Left,SDIAppForm->Height,SDIAppForm->Width);
    fprintf(out,"%i %i %i %i // Template\n", Form6->Top,Form6->Left,Form6->Height,Form6->Width);
   fprintf(out,"%i %i // Fit\n", Form14->Top,Form14->Left);
   fprintf(out,"%i %i // CF\n", Form9->Top,Form9->Left);
   fprintf(out,"%i %i // Options\n", OKBottomDlg->Top,OKBottomDlg->Left);
   fprintf(out,"%i %i // Ident\n", Form5->Top,Form5->Left);
   fprintf(out,"%s // InDir\n", AnsiString(SDIAppForm->Edit14->Text).c_str());
  fclose(out);
   ShowMessage("Options Saved");
}
//---------------------------------------------------------------------------


void __fastcall TOKBottomDlg::CheckBox2Click(TObject *Sender)
{
if ((OKBottomDlg->CheckBox2->Checked==true))
{
float xf,yf;

Form10->Series1->Clear();

   FILE *strm;
  strm = fopen(AnsiString(OKBottomDlg->Edit10->Text).c_str(), "rt");
 do
   {
   fscanf(strm,"%g %g", &xf, &yf);
     if ((OKBottomDlg->CheckBox7->Checked==true) & (xf < 1500.0))
  {
    xf=xf*10.0;
  }
   Form10->Series1->AddXY(xf,yf,' ',clBlack);
    }
while(!feof(strm));
   fclose(strm);
   			Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
				Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
}
else
{
   Form10->Series1->Clear();
   Form10->Series1->AddXY(2000.0,1.0,' ',clBlack);
   Form10->Series1->AddXY(10000.0,1.0,' ',clBlack);
}
}
//---------------------------------------------------------------------------

void __fastcall TOKBottomDlg::CheckBox1Click(TObject *Sender)
{
if (OKBottomDlg->CheckBox1->Checked==true)
{
 Form12->Series1->Clear();
 float xf,yf;

Form12->Series1->Clear();

   FILE *strm;
  strm = fopen(AnsiString(OKBottomDlg->Edit11->Text).c_str(), "rt");
   if (strm==NULL) ShowMessage("correction file not found");
   else {
        int idx=0;
        do
        {
        idx++;
        fscanf(strm,"%g %g", &xf, &yf);

        Form12->Series1->AddXY(idx,yf,' ',clBlack);
        }
while(!feof(strm));
   fclose(strm);
   }
   }
}
//---------------------------------------------------------------------------

void __fastcall TOKBottomDlg::Button3Click(TObject *Sender)
{
float xf,yf;
OpenDialog1->FileName=Edit11->Text;
if (OpenDialog1->Execute())
{
Edit11->Text=OpenDialog1->FileName;
float xf,yf;

Form12->Series1->Clear();

   FILE *strm;
  strm = fopen(AnsiString(OKBottomDlg->Edit11->Text).c_str(), "rt");
   int idx=0;
 do
   {
   idx++;
   fscanf(strm,"%g %g", &xf, &yf);

   Form12->Series1->AddXY(idx,yf,' ',clBlack);
    }
while(!feof(strm));
   fclose(strm);
}
}
//---------------------------------------------------------------------------



