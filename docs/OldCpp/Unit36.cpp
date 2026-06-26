//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop
#include <stdio.h>
#include <fcntl.h>
#include <io.h>
#include <iostream.h>
#include <fstream.h>
#include "Unit36.h"
#include "Unit13.h"
#include "SDIMain.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm36 *Form36;
//---------------------------------------------------------------------------
__fastcall TForm36::TForm36(TComponent* Owner)
	: TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm36::Button1Click(TObject *Sender)
{

  SDIAppForm->OpenDialog->FileName = "";
	 SDIAppForm->OpenDialog->Filter = "Avantes Binary Files (*.roh)|*.roh|Avantes Files (*.trt)|*.trt|All Files (*.*)|*.*";
	AnsiString fp;
	 SDIAppForm->OpenDialog->InitialDir=SDIAppForm->Edit14->Text;
	if (SDIAppForm->OpenDialog->Execute())
  {
int st, stp;
  switch(Form36->RadioGroup1->ItemIndex)
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
  Form36->Memo1->Lines->Append(AnsiString(SDIAppForm->OpenDialog->Files->Strings[I]).c_str());
	}
	}

}
//---------------------------------------------------------------------------
void __fastcall TForm36::Button4Click(TObject *Sender)
{
 void openfile(AnsiString nomefile);
 void appfile(AnsiString nomefile);

 SDIAppForm->Chart1->BottomAxis->Automatic=true;
  SDIAppForm->Chart1->LeftAxis->Automatic=true;



	 for (int I = 0; I < Form36->Memo1->Lines->Count; I+=2)
	{

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


	 AnsiString fvv1= AnsiString(Form36->Memo1->Lines->Strings[I].c_str());
	 AnsiString fvv2= AnsiString(Form36->Memo1->Lines->Strings[I+1].c_str());
	  int w; AnsiString ass;

	  openfile(fvv1.c_str());
			appfile(fvv2.c_str());
	   ass = ChangeFileExt(fvv1,".jnd");

	   FILE *out;

   out = fopen(ass.c_str(), "wt");

	  for (w=SDIAppForm->Series1->FirstValueIndex;w<SDIAppForm->Series1->LastValueIndex+1;w++)
	  {
		fprintf(out,"%f %f\n", SDIAppForm->Series1->XValues->Value[w], SDIAppForm->Series1->YValues->Value[w]);
	  }
	 fclose(out);

	  }
  }
//---------------------------------------------------------------------------
void __fastcall TForm36::Button6Click(TObject *Sender)
{
Form36->Memo1->Clear();
}
//---------------------------------------------------------------------------
void __fastcall TForm36::Button2Click(TObject *Sender)
{
 void openfile(AnsiString nomefile);
  void compfile(AnsiString nomefile);
  float average[65535];
	float ss[65535];

 for (int I = 0; I < Form36->Memo1->Lines->Count; I ++)
	{
		openfile(AnsiString(Form36->Memo1->Lines->Strings[I].c_str()));
		  for (int w=SDIAppForm->Series1->FirstValueIndex;w<SDIAppForm->Series1->LastValueIndex+1;w++)
	  {
  if (I==0) average[w]=SDIAppForm->Series1->YValues->Value[w];
  else  average[w]+=SDIAppForm->Series1->YValues->Value[w];

	}
}

 int wnum=Form36->Memo1->Lines->Count;

   if (CheckBox1->Checked) {


 for (int II = 0; II < Form36->Memo1->Lines->Count; II ++)
	{
		openfile(AnsiString(Form36->Memo1->Lines->Strings[II].c_str()));
		  for (int ww=SDIAppForm->Series1->FirstValueIndex;ww<SDIAppForm->Series1->LastValueIndex+1;ww++)
	  {
	  if (II==0) ss[ww]=pow(SDIAppForm->Series1->YValues->Value[ww]-average[ww]/wnum,2);
	  else ss[ww]+=pow(SDIAppForm->Series1->YValues->Value[ww]-average[ww]/wnum,2);
	}
	}

}
openfile(AnsiString(Form36->Memo1->Lines->Strings[0].c_str()));

 Form13->StringGrid1->Refresh();

	 for (int w=SDIAppForm->Series1->FirstValueIndex;w<SDIAppForm->Series1->LastValueIndex+1;w++)
	  {
	   SDIAppForm->Series1->YValues->Value[w]=average[w]/wnum;
	   }

  if (CheckBox1->Checked) {
	   compfile(AnsiString(Form36->Memo1->Lines->Strings[(Form36->Memo1->Lines->Count)-1].c_str()));
			int sc,lc,jfin;
			  sc=SDIAppForm->Chart1->SeriesCount();

			for (int j=0;j<=Form13->StringGrid1->RowCount;j++)
			 {
			 if   (Form13->StringGrid1->Cells[1][j] =="")
			  {
			  Form13->StringGrid1->Cells[1][j]= AnsiString(Form36->Memo1->Lines->Strings[(Form36->Memo1->Lines->Count)-1].c_str());
			   break;
			   }
				}

		 for (int w=SDIAppForm->Series1->FirstValueIndex;w<SDIAppForm->Series1->LastValueIndex+1;w++)
	  {
		 SDIAppForm->Chart1->Series[6]->YValues->Value[w]=sqrt(ss[w])/wnum;
	   }
	   }
			Form13->StringGrid1->Refresh();
		  SDIAppForm->Full_YClick(Sender);

}
//---------------------------------------------------------------------------

void __fastcall TForm36::Button3Click(TObject *Sender)
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
		Form36->Memo1->Lines->Append(buf);
		goto ag;
   }

fclose(in);
   }
}
//---------------------------------------------------------------------------

void __fastcall TForm36::Button5Click(TObject *Sender)
{
Form36->Close();
}
//---------------------------------------------------------------------------

void __fastcall TForm36::Button7Click(TObject *Sender)
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

Form36->Memo1->Lines->SaveToFile(SDIAppForm->SaveDialog1->FileName);

}
}
//---------------------------------------------------------------------------


void __fastcall TForm36::LoadFile1Click(TObject *Sender)
{
Form36->Button3Click(Sender);
}
//---------------------------------------------------------------------------

void __fastcall TForm36::SaveFile1Click(TObject *Sender)
{
 Form36->Button7Click(Sender);
}
//---------------------------------------------------------------------------

void __fastcall TForm36::Close1Click(TObject *Sender)
{
  Form36->Button6Click(Sender);
}
//---------------------------------------------------------------------------

